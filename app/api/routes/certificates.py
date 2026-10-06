from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.schemas.certificates import CertificateMetadataResponse
from app.core.exceptions import CertificateNotFoundError
from app.db.models.certificate import Certificate
from app.db.session import get_db
from app.services.certificate_service import build_job_certificate_archive, resolve_certificate, resolve_certificate_file

router = APIRouter(prefix="/api", tags=["certificates"])


@router.get("/certificates/{certificate_id}/", response_model=CertificateMetadataResponse)
def get_certificate_metadata(certificate_id: str, db: Session = Depends(get_db)) -> CertificateMetadataResponse:
    try:
        certificate = resolve_certificate(db, certificate_id)
    except CertificateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Certificate not found.") from exc

    recipient = certificate.recipient
    return CertificateMetadataResponse(
        certificate_id=certificate.id,
        recipient_id=recipient.id,
        job_id=certificate.job_id,
        recipient_name=recipient.name,
        recipient_email=recipient.email,
        storage_path=certificate.storage_path,
        created_at=str(certificate.created_at),
    )


@router.get("/certificates/{certificate_id}/download/")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)) -> FileResponse:
    try:
        file_path, certificate = resolve_certificate_file(db, certificate_id)
    except CertificateNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Certificate not found.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if certificate.recipient.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="Certificate is not available for download.")
    return FileResponse(path=file_path, media_type="application/pdf", filename=f"{certificate_id}.pdf")


@router.get("/jobs/{job_id}/certificates/archive/")
def download_job_certificate_archive(job_id: str, db: Session = Depends(get_db)) -> Response:
    try:
        archive_bytes = build_job_certificate_archive(db, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{job_id}-certificates.zip"'},
    )
