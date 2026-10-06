from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.job import GenerationJob, JobStatus
from app.db.models.recipient import Recipient, RecipientStatus
from app.services.certificate_service import generate_certificate_for_recipient, update_final_job_status

logger = logging.getLogger(__name__)


def _normalize_name(value: str) -> str:
    return value.strip()


def _is_valid_email(value: str) -> bool:
    try:
        validate_email(value, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def create_generation_job(session: Session, payload: Any) -> GenerationJob:
    recipients = payload.recipients
    if not recipients:
        raise HTTPException(status_code=422, detail="At least one recipient is required.")
    if len(recipients) > settings.MAX_RECIPIENTS_PER_JOB:
        raise HTTPException(status_code=422, detail=f"A job may contain at most {settings.MAX_RECIPIENTS_PER_JOB} recipients.")

    seen_emails: set[str] = set()
    job = GenerationJob(
        organization_name=payload.certificate.organization_name,
        course_name=payload.certificate.course_name,
        issue_date=payload.certificate.issue_date,
        signatory_name=payload.certificate.signatory_name,
        status=JobStatus.PENDING.value,
    )
    session.add(job)
    session.flush()

    for item in recipients:
        normalized_email = str(item.email).strip().lower()
        normalized_name = _normalize_name(item.name)

        if not normalized_email or not _is_valid_email(normalized_email):
            recipient = Recipient(
                job_id=job.id,
                name=normalized_name,
                email=normalized_email,
                status=RecipientStatus.REJECTED.value,
                validation_error="Invalid email address.",
            )
            session.add(recipient)
            continue

        if normalized_email in seen_emails:
            recipient = Recipient(
                job_id=job.id,
                name=normalized_name,
                email=normalized_email,
                status=RecipientStatus.REJECTED.value,
                validation_error="Duplicate email within the same job.",
            )
            session.add(recipient)
            continue
        seen_emails.add(normalized_email)
        recipient = Recipient(
            job_id=job.id,
            name=normalized_name,
            email=normalized_email,
            status=RecipientStatus.PENDING.value,
        )
        session.add(recipient)

    session.flush()
    job.total_count = session.query(Recipient).filter(Recipient.job_id == job.id).count()
    job.pending_count = session.query(Recipient).filter(Recipient.job_id == job.id, Recipient.status == RecipientStatus.PENDING.value).count()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job_by_id(session: Session, job_id: str) -> GenerationJob:
    job = session.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def refresh_job_metrics(session: Session, job_id: str) -> GenerationJob:
    job = get_job_by_id(session, job_id)
    recipients = session.query(Recipient).filter(Recipient.job_id == job_id).all()
    job.total_count = len(recipients)
    job.pending_count = sum(1 for rec in recipients if rec.status == RecipientStatus.PENDING.value)
    job.processing_count = sum(1 for rec in recipients if rec.status == RecipientStatus.PROCESSING.value)
    job.successful_count = sum(1 for rec in recipients if rec.status == RecipientStatus.COMPLETED.value)
    job.failed_count = sum(1 for rec in recipients if rec.status == RecipientStatus.FAILED.value)
    job.rejected_count = sum(1 for rec in recipients if rec.status == RecipientStatus.REJECTED.value)
    if job.started_at is None and job.total_count:
        job.started_at = datetime.now(timezone.utc)

    if job.total_count == 0:
        job.status = JobStatus.FAILED.value
    elif job.successful_count > 0 and (job.failed_count > 0 or job.rejected_count > 0):
        job.status = JobStatus.PARTIALLY_COMPLETED.value
    elif job.successful_count == job.total_count:
        job.status = JobStatus.COMPLETED.value
    elif job.successful_count == 0 and (job.failed_count > 0 or job.rejected_count > 0):
        job.status = JobStatus.FAILED.value
    elif job.pending_count > 0:
        job.status = JobStatus.PENDING.value
    elif job.processing_count > 0:
        job.status = JobStatus.PROCESSING.value
    else:
        job.status = JobStatus.FAILED.value

    if job.status in {JobStatus.COMPLETED.value, JobStatus.PARTIALLY_COMPLETED.value, JobStatus.FAILED.value}:
        job.completed_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    return job


def process_job(session: Session, job_id: str) -> GenerationJob:
    job = get_job_by_id(session, job_id)
    if job.status in {JobStatus.COMPLETED.value, JobStatus.PARTIALLY_COMPLETED.value, JobStatus.FAILED.value}:
        return job

    if job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    job.status = JobStatus.PROCESSING.value
    session.add(job)
    session.commit()

    recipients = session.execute(
        select(Recipient).where(
            Recipient.job_id == job_id,
            Recipient.status.in_([RecipientStatus.PENDING.value]),
        )
    ).scalars().all()

    for recipient in recipients:
        recipient.status = RecipientStatus.PROCESSING.value
        recipient.processed_at = datetime.now(timezone.utc)
        session.add(recipient)
        session.commit()
        try:
            certificate = generate_certificate_for_recipient(session, job, recipient)
            recipient.status = RecipientStatus.COMPLETED.value
            recipient.processed_at = datetime.now(timezone.utc)
            recipient.processing_error = None
            session.add(recipient)
            session.add(certificate)
            session.commit()
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.exception("Certificate generation failed for recipient %s in job %s", recipient.id, job.id)
            recipient.status = RecipientStatus.FAILED.value
            recipient.processing_error = str(exc)
            recipient.processed_at = datetime.now(timezone.utc)
            session.add(recipient)
            session.commit()

    final_job = refresh_job_metrics(session, job_id)
    return final_job


def process_pending_jobs() -> None:
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        jobs = session.execute(
            select(GenerationJob).where(GenerationJob.status.in_([JobStatus.PENDING.value, JobStatus.PROCESSING.value]))
        ).scalars().all()
        for job in jobs:
            process_job(session, job.id)
