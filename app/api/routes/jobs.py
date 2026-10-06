from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas.certificates import CertificateResult, CertificateListResponse
from app.api.schemas.jobs import BulkJobRequest, JobCreateResponse, JobDetailResponse, JobSummaryResponse
from app.db.models.job import GenerationJob
from app.db.models.recipient import Recipient, RecipientStatus
from app.db.session import get_db
from app.services.certificate_service import get_download_url
from app.services.job_service import create_generation_job, get_job_by_id, process_job, refresh_job_metrics

router = APIRouter(prefix="/api", tags=["jobs"])


@router.post("/jobs/", response_model=JobCreateResponse, status_code=202)
def create_job(payload: BulkJobRequest, db: Session = Depends(get_db)) -> JobCreateResponse:
    job = create_generation_job(db, payload)
    return JobCreateResponse(job_id=job.id, status=job.status, message="Job accepted and queued for processing.")


@router.get("/jobs/{job_id}/", response_model=JobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobDetailResponse:
    job = get_job_by_id(db, job_id)
    refresh_job_metrics(db, job.id)
    db.refresh(job)
    percentage = 0.0
    if job.total_count:
        percentage = ((job.total_count - job.pending_count) / job.total_count) * 100.0
    return JobDetailResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        pending_count=job.pending_count,
        processing_count=job.processing_count,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        rejected_count=job.rejected_count,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress_percentage=round(percentage, 2),
        failure_summary=job.error_message,
    )


@router.get("/jobs/{job_id}/certificates/", response_model=CertificateListResponse)
def list_job_certificates(
    job_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> CertificateListResponse:
    get_job_by_id(db, job_id)
    recipients = (
        db.query(Recipient)
        .filter(Recipient.job_id == job_id)
        .order_by(Recipient.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: list[CertificateResult] = []
    for recipient in recipients:
        certificate = recipient.certificate
        error_code = None
        error_message = None
        if recipient.status == RecipientStatus.REJECTED.value:
            error_code = "recipient_rejected"
            error_message = recipient.validation_error or "Recipient was rejected."
        elif recipient.status == RecipientStatus.FAILED.value:
            error_code = "certificate_generation_failed"
            error_message = recipient.processing_error or "Certificate generation failed."

        items.append(
            CertificateResult(
                recipient_id=recipient.id,
                recipient_name=recipient.name,
                recipient_email=recipient.email,
                status=recipient.status,
                certificate_id=certificate.id if certificate else None,
                download_url=get_download_url(job_id, certificate.id) if certificate else None,
                error_code=error_code,
                error_message=error_message,
            )
        )

    total = db.query(Recipient).filter(Recipient.job_id == job_id).count()
    return CertificateListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/jobs/{job_id}/process/")
def trigger_job_processing(job_id: str, db: Session = Depends(get_db)) -> JobSummaryResponse:
    job = get_job_by_id(db, job_id)
    process_job(db, job.id)
    db.refresh(job)
    return JobSummaryResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        pending_count=job.pending_count,
        processing_count=job.processing_count,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        rejected_count=job.rejected_count,
        progress_percentage=round(((job.total_count - job.pending_count) / job.total_count * 100.0) if job.total_count else 0.0, 2),
    )
