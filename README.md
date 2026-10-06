
# Bulk Certificate Generator API

A production-style FastAPI backend for creating bulk certificate jobs, validating recipients individually, generating one PDF per valid recipient, tracking progress, and exposing certificate metadata and downloads.

## Overview

The service accepts a bulk request containing certificate metadata and a list of recipients, persists the job and recipient records in PostgreSQL, and then processes valid recipients asynchronously in a background worker. Each recipient is evaluated independently, so one failure does not abort the entire batch.

## Features

- FastAPI REST API with Pydantic validation
- PostgreSQL + SQLAlchemy 2.x + Alembic migrations
- Unique job and certificate identifiers
- Per-recipient validation and status tracking
- Independent failure handling without aborting the whole job
- PDF generation with ReportLab using a single certificate template
- Safe filesystem storage with path validation
- Job status and certificate listing endpoints
- Download endpoint for generated PDFs
- Automated pytest coverage for core flows

## Technology Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- Pydantic
- ReportLab
- Uvicorn
- Docker Compose
- Pytest
- HTTPX

## Prerequisites

- Python 3.12 or newer
- PostgreSQL running locally or via Docker
- virtualenv or venv
- Docker Desktop (optional for local PostgreSQL)

## Project Structure

```text
bulk-certificate-generator/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── jobs.py
│   │   │   └── certificates.py
│   │   └── schemas/
│   │       ├── jobs.py
│   │       └── certificates.py
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── job.py
│   │       ├── recipient.py
│   │       └── certificate.py
│   ├── services/
│   │   ├── certificate_service.py
│   │   ├── job_service.py
│   │   ├── pdf_generator.py
│   │   └── storage_service.py
│   ├── workers/
│   │   └── processor.py
│   ├── main.py
│   └── __init__.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/
│   ├── conftest.py
│   ├── test_jobs.py
│   ├── test_certificates.py
│   ├── test_failure_handling.py
│   └── test_pdf_generator.py
├── storage/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── README.md
└── .venv/
```

## Database Schema

The application stores the following core records:

- generation_jobs
  - id
  - status
  - organization_name
  - course_name
  - issue_date
  - signatory_name
  - total_count
  - pending_count
  - processing_count
  - successful_count
  - failed_count
  - rejected_count
  - created_at
  - started_at
  - completed_at
  - error_message

- recipients
  - id
  - job_id
  - name
  - email
  - status
  - validation_error
  - processing_error
  - created_at
  - processed_at

- certificates
  - id
  - recipient_id
  - job_id
  - storage_path
  - created_at
  - checksum

Relationships are enforced with foreign keys and the recipient-to-certificate mapping uses a one-to-one relationship to prevent duplicates for a single generation attempt.

## Local Setup

### Windows

```powershell
cd "c:\Users\adars\OneDrive\Desktop\Bulk Certificate Generator"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux/macOS

```bash
cd /path/to/bulk-certificate-generator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Environment Configuration

Create a local `.env` file based on `.env.example`:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/certificate_generator
STORAGE_DIR=./storage
MAX_RECIPIENTS_PER_JOB=1000
LOG_LEVEL=INFO
WORKER_POLL_INTERVAL_SECONDS=5
```

## PostgreSQL with Docker Compose

```bash
docker compose up -d postgres
```

Then confirm the database is available:

```bash
psql postgresql://postgres:postgres@localhost:5432/certificate_generator
```

## Database Migration

```bash
python -m alembic upgrade head
```

If you need to generate a fresh migration:

```bash
python -m alembic revision --autogenerate -m "describe change"
```

## Application Startup

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI is available at:

```text
http://localhost:8000/docs
```

## Worker Startup

The project includes a simple local background worker. Run it in a separate terminal:

```bash
python -m app.workers.processor
```

This is intentionally simple and suitable for local development. It does not provide durable processing across full application restarts without the surrounding orchestration layer.

## Automated Tests

```bash
python -m pytest -q
```

## API Endpoints

### POST /api/jobs/

Creates a new certificate generation job.

Example request:

```json
{
  "certificate": {
    "course_name": "Python Backend Development",
    "organization_name": "ABC Academy",
    "issue_date": "2026-10-06",
    "signatory_name": "John Smith"
  },
  "recipients": [
    { "name": "Alice Johnson", "email": "alice@example.com" },
    { "name": "Bob Williams", "email": "bob@example.com" },
    { "name": "Charlie Brown", "email": "invalid-email" }
  ]
}
```

Response:

```json
{
  "job_id": "<uuid>",
  "status": "PENDING",
  "message": "Job accepted and queued for processing."
}
```

### GET /api/jobs/{job_id}/

Returns job-level progress and counts.

Example response:

```json
{
  "job_id": "<uuid>",
  "status": "COMPLETED",
  "total_count": 2,
  "pending_count": 0,
  "processing_count": 0,
  "successful_count": 2,
  "failed_count": 0,
  "rejected_count": 0,
  "created_at": "2026-10-06T12:00:00Z",
  "started_at": "2026-10-06T12:00:10Z",
  "completed_at": "2026-10-06T12:00:22Z",
  "progress_percentage": 100.0,
  "failure_summary": null
}
```

### POST /api/jobs/{job_id}/process/

Manually triggers processing for an existing job. This is useful when a job was created but the worker has not yet started, or when you want to process a queued job on demand.

Example response:

```json
{
  "job_id": "<uuid>",
  "status": "PROCESSING",
  "total_count": 2,
  "pending_count": 0,
  "processing_count": 1,
  "successful_count": 1,
  "failed_count": 0,
  "rejected_count": 0,
  "progress_percentage": 50.0
}
```

### GET /api/jobs/{job_id}/certificates/

Returns a paginated list of recipient outcomes and certificate metadata.

Example response:

```json
{
  "items": [
    {
      "recipient_id": "<uuid>",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "COMPLETED",
      "certificate_id": "<uuid>",
      "download_url": "/api/certificates/<uuid>/download/",
      "error_code": null,
      "error_message": null
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### GET /api/certificates/{certificate_id}/

Returns certificate metadata without streaming the PDF.

### GET /api/certificates/{certificate_id}/download/

Downloads the generated PDF as `application/pdf`.

### GET /api/jobs/{job_id}/certificates/archive/

Downloads all successful certificates for the job as a ZIP archive.

## Submit a Job and Retrieve Certificates

Submit a generation request to create a job. Save the returned `job_id` for the following requests:

```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "certificate": {
      "course_name": "Python Backend Development",
      "organization_name": "ABC Academy",
      "issue_date": "2026-10-06",
      "signatory_name": "John Smith"
    },
    "recipients": [
      {"name": "Alice Johnson", "email": "alice@example.com"},
      {"name": "Bob Williams", "email": "bob@example.com"}
    ]
  }'
```

The background worker processes queued jobs. Alternatively, trigger a job manually:

```bash
curl -X POST http://localhost:8000/api/jobs/<job_id>/process/
```

Check job progress and recipient outcomes:

```bash
curl http://localhost:8000/api/jobs/<job_id>/
curl http://localhost:8000/api/jobs/<job_id>/certificates/
```

For each recipient with `COMPLETED` status, use its `download_url` to retrieve the PDF:

```bash
curl -L http://localhost:8000/api/certificates/<certificate_id>/download/ \
  --output certificate.pdf
```

To download all successfully generated PDFs together:

```bash
curl -L http://localhost:8000/api/jobs/<job_id>/certificates/archive/ \
  --output certificates.zip
```

## Request-Level vs Recipient-Level Validation

Request-level validation fails when the overall structure is invalid: missing certificate information, empty recipient list, or an excessively large job. In those cases, the API returns a 4xx response and the request is rejected before any processing begins.

Recipient-level validation is different. Each recipient is parsed and validated individually. Invalid recipients are stored with a `REJECTED` status and are not allowed to block valid recipients in the same job. This matches the requirement that valid work continues while invalid entries are recorded for reporting.

## Independent Failure Handling

Each recipient is processed independently:

1. the recipient is marked as `PROCESSING`
2. the PDF is generated
3. the certificate metadata is persisted
4. the recipient is marked as `COMPLETED`
5. if generation fails, the recipient is marked as `FAILED` and the next recipient continues

This design prevents one PDF failure from stopping the entire generation job.

## Background Processing Design

The application uses a simple local worker process that polls the database for pending jobs. This keeps the HTTP request short and lets the client poll the status endpoint.

Limitations:

- job execution is not durable across server restarts unless you add a persistent queue or a more resilient scheduler
- the worker runs in one process locally, which is suitable for demos and local development rather than production

## Job Status Model

The application uses the following terminal and processing states:

- `PENDING`: job created, not yet being processed
- `PROCESSING`: job or recipients are actively being processed
- `COMPLETED`: all eligible recipients succeeded
- `PARTIALLY_COMPLETED`: at least one recipient succeeded and at least one failed or was rejected
- `FAILED`: no successful certificates were produced or the job failed at a job level

## Duplicate Email Handling

Duplicate emails in the same job are explicitly rejected. The duplicate recipient is stored with a validation error, while all other valid recipients continue processing normally.

## Security Notes

- the API is unauthenticated by design for the assignment
- storage paths are validated to stay within the configured root directory
- filesystem paths are never exposed to clients directly
- generated files are stored on disk rather than in PostgreSQL to reduce database bloat and improve scalability

## Important Design Decisions

- FastAPI was selected because it matches Python services well and exposes clean validation and HTTP semantics.
- PostgreSQL is used for transactional reliability and structured querying.
- SQLAlchemy and Alembic allow schema evolution and maintainable data access.
- PDFs are stored on disk because they are large binary objects and do not need to live in the database for this assignment.
- A single job returns an ID so clients can poll without waiting for the entire batch to complete.
- Each recipient has independent status so failures can be isolated and reported accurately.
- Progress is derived from the database record counts to avoid drift and inconsistent totals.

## Future Scope

- retry logic for failed PDF generation
- ZIP archive download of all successful certificates
- job cancellation
- idempotency keys
- S3-compatible storage backend
- authentication and rate limiting
- pagination and filtering for long job histories

## Known Limitations

- local worker processing is not production-grade durable job orchestration
- no authentication or authorization is implemented
- certificate storage is currently local filesystem-based
- there is no distributed concurrency protection beyond the local database transaction model

## Learning Outcomes

This project demonstrates practical backend work in:

- API design and validation
- database modeling and migration management
- asynchronous processing patterns
- safe filesystem handling
- test-driven reliability checks
- interview-ready system design reasoning
#
