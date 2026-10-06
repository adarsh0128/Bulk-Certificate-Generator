from __future__ import annotations

from pydantic import BaseModel


class CertificateResult(BaseModel):
    recipient_id: str
    recipient_name: str
    recipient_email: str
    status: str
    certificate_id: str | None
    download_url: str | None
    error_code: str | None = None
    error_message: str | None = None


class CertificateListResponse(BaseModel):
    items: list[CertificateResult]
    total: int
    limit: int
    offset: int


class CertificateMetadataResponse(BaseModel):
    certificate_id: str
    recipient_id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    storage_path: str
    created_at: str
