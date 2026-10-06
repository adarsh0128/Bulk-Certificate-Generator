from __future__ import annotations

import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CertificateGenerationError, CertificateNotFoundError
from app.db.models.certificate import Certificate
from app.db.models.job import GenerationJob, JobStatus
from app.db.models.recipient import Recipient, RecipientStatus
from app.services.pdf_generator import generate_certificate_pdf
from app.services.storage_service import StorageService


def build_certificate_payload(job: GenerationJob, recipient: Recipient) -> dict[str, str]:
    return {
        "organization_name": job.organization_name or "",
        "course_name": job.course_name or "",
        "recipient_name": recipient.name,
        "issue_date": job.issue_date.strftime("%Y-%m-%d") if job.issue_date else "",
        "signatory_name": job.signatory_name or "",
        "certificate_id": str(uuid.uuid4()),
    }


def generate_certificate_for_recipient(session: Session, job: GenerationJob, recipient: Recipient) -> Certificate:
    storage = StorageService()
    cert_id = str(uuid.uuid4())
    relative_path = StorageService.build_relative_path(job.id, cert_id)
    file_path = storage.ensure_safe_path(relative_path)

    payload = build_certificate_payload(job, recipient)
    payload["certificate_id"] = cert_id

    try:
        generate_certificate_pdf(
            file_path,
            organization_name=payload["organization_name"],
            course_name=payload["course_name"],
            recipient_name=payload["recipient_name"],
            issue_date=payload["issue_date"],
            signatory_name=payload["signatory_name"],
            certificate_id=payload["certificate_id"],
        )
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise CertificateGenerationError("Generated PDF is empty or missing.")

        checksum = StorageService.compute_checksum(file_path)
        certificate = Certificate(
            id=str(uuid.uuid4()),
            recipient_id=recipient.id,
            job_id=job.id,
            storage_path=relative_path,
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
        )
        session.add(certificate)
        session.flush()
        session.commit()
        return certificate
    except Exception:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        session.rollback()
        raise


def list_certificate_rows(session: Session, job_id: str, limit: int, offset: int):
    stmt = (
        select(Recipient, Certificate)
        .outerjoin(Certificate, Certificate.recipient_id == Recipient.id)
        .where(Recipient.job_id == job_id)
        .order_by(Recipient.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return session.execute(stmt).all()


def resolve_certificate(session: Session, certificate_id: str) -> Certificate:
    certificate = session.get(Certificate, certificate_id)
    if certificate is None:
        raise CertificateNotFoundError("Certificate not found.")
    return certificate


def resolve_certificate_file(session: Session, certificate_id: str) -> tuple[Path, Certificate]:
    certificate = resolve_certificate(session, certificate_id)
    storage = StorageService()
    file_path = storage.ensure_safe_path(certificate.storage_path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError("Certificate file is missing or unavailable.")
    return file_path, certificate


def get_download_url(job_id: str, certificate_id: str) -> str:
    return f"/api/certificates/{certificate_id}/download/"


def build_job_certificate_archive(session: Session, job_id: str) -> bytes:
    successful_certificates = (
        session.query(Certificate)
        .join(Recipient, Recipient.id == Certificate.recipient_id)
        .filter(Recipient.job_id == job_id, Recipient.status == RecipientStatus.COMPLETED.value)
        .order_by(Certificate.created_at.asc())
        .all()
    )

    if not successful_certificates:
        raise FileNotFoundError("No successful certificates are available for this job.")

    archive_buffer = BytesIO()
    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for certificate in successful_certificates:
            file_path = StorageService().ensure_safe_path(certificate.storage_path)
            if not file_path.exists() or not file_path.is_file():
                continue

            safe_name = (certificate.recipient.name or certificate.recipient.email).strip()
            safe_name = "".join(char if char.isalnum() or char in {"_", "-", ".", " "} else "_" for char in safe_name)
            safe_name = safe_name.strip() or certificate.id
            archive.write(file_path, arcname=f"{safe_name}.pdf")

    return archive_buffer.getvalue()


def update_final_job_status(session: Session, job: GenerationJob) -> GenerationJob:
    recipients = session.query(Recipient).filter(Recipient.job_id == job.id).all()
    job.total_count = len(recipients)
    job.pending_count = sum(1 for item in recipients if item.status == RecipientStatus.PENDING.value)
    job.processing_count = sum(1 for item in recipients if item.status == RecipientStatus.PROCESSING.value)
    job.successful_count = sum(1 for item in recipients if item.status == RecipientStatus.COMPLETED.value)
    job.failed_count = sum(1 for item in recipients if item.status == RecipientStatus.FAILED.value)
    job.rejected_count = sum(1 for item in recipients if item.status == RecipientStatus.REJECTED.value)

    if job.total_count == 0:
        job.status = JobStatus.FAILED.value
    elif job.successful_count > 0 and (job.failed_count > 0 or job.rejected_count > 0):
        job.status = JobStatus.PARTIALLY_COMPLETED.value
    elif job.successful_count == job.total_count:
        job.status = JobStatus.COMPLETED.value
    elif job.successful_count == 0 and (job.failed_count > 0 or job.rejected_count > 0):
        job.status = JobStatus.FAILED.value
    elif job.started_at is None:
        job.status = JobStatus.PENDING.value
    elif job.processing_count > 0 or job.pending_count > 0:
        job.status = JobStatus.PROCESSING.value
    else:
        job.status = JobStatus.FAILED.value

    if job.status in {JobStatus.COMPLETED.value, JobStatus.PARTIALLY_COMPLETED.value, JobStatus.FAILED.value}:
        job.completed_at = datetime.now(timezone.utc)
    elif job.status == JobStatus.PROCESSING.value and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)

    session.add(job)
    session.commit()
    return job
