from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CertificateRequest(BaseModel):
    course_name: str = Field(..., min_length=1)
    organization_name: str = Field(..., min_length=1)
    issue_date: date
    signatory_name: str = Field(..., min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class RecipientRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str

    model_config = ConfigDict(str_strip_whitespace=True)


class BulkJobRequest(BaseModel):
    certificate: CertificateRequest
    recipients: list[RecipientRequest] = Field(..., min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobDetailResponse(BaseModel):
    job_id: str
    status: str
    total_count: int
    pending_count: int
    processing_count: int
    successful_count: int
    failed_count: int
    rejected_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    progress_percentage: float
    failure_summary: str | None = None


class JobSummaryResponse(BaseModel):
    job_id: str
    status: str
    total_count: int
    pending_count: int
    processing_count: int
    successful_count: int
    failed_count: int
    rejected_count: int
    progress_percentage: float
