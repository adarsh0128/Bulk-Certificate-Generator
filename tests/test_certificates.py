from __future__ import annotations

from app.db.models.certificate import Certificate
from app.db.models.recipient import RecipientStatus
from app.services.job_service import process_job


def create_valid_job(client):
    payload = {
        "certificate": {
            "course_name": "Python Backend Development",
            "organization_name": "ABC Academy",
            "issue_date": "2026-10-06",
            "signatory_name": "John Smith",
        },
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Williams", "email": "bob@example.com"},
        ],
    }
    response = client.post("/api/jobs/", json=payload)
    return response.json()["job_id"]


def test_retrieving_certificate_metadata(client_and_db):
    client, SessionLocal = client_and_db
    job_id = create_valid_job(client)
    with SessionLocal() as session:
        process_job(session, job_id)

    response = client.get(f"/api/jobs/{job_id}/certificates/")
    items = response.json()["items"]
    cert_id = items[0]["certificate_id"]
    metadata = client.get(f"/api/certificates/{cert_id}/")
    assert metadata.status_code == 200
    payload = metadata.json()
    assert payload["certificate_id"] == cert_id
    assert payload["recipient_name"]


def test_downloading_generated_pdf(client_and_db):
    client, SessionLocal = client_and_db
    job_id = create_valid_job(client)
    with SessionLocal() as session:
        process_job(session, job_id)

    cert_id = client.get(f"/api/jobs/{job_id}/certificates/").json()["items"][0]["certificate_id"]
    response = client.get(f"/api/certificates/{cert_id}/download/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert len(response.content) > 1000


def test_downloading_all_successful_certificates_as_zip(client_and_db):
    client, SessionLocal = client_and_db
    job_id = create_valid_job(client)
    with SessionLocal() as session:
        process_job(session, job_id)

    response = client.get(f"/api/jobs/{job_id}/certificates/archive/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert len(response.content) > 1000


def test_missing_pdf_file_returns_404(client_and_db):
    client, SessionLocal = client_and_db
    job_id = create_valid_job(client)
    with SessionLocal() as session:
        process_job(session, job_id)

    cert_id = client.get(f"/api/jobs/{job_id}/certificates/").json()["items"][0]["certificate_id"]
    with SessionLocal() as session:
        certificate = session.query(Certificate).filter(Certificate.id == cert_id).one()
        from pathlib import Path
        from app.core.config import settings
        file_path = Path(settings.STORAGE_DIR) / certificate.storage_path
        if file_path.exists():
            file_path.unlink()

    response = client.get(f"/api/certificates/{cert_id}/download/")
    assert response.status_code == 404


def test_partially_completed_job_status_after_failure(client_and_db):
    client, SessionLocal = client_and_db
    payload = {
        "certificate": {
            "course_name": "Python Backend Development",
            "organization_name": "ABC Academy",
            "issue_date": "2026-10-06",
            "signatory_name": "John Smith",
        },
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Williams", "email": "bob@example.com"},
        ],
    }
    create_response = client.post("/api/jobs/", json=payload)
    job_id = create_response.json()["job_id"]

    from app.services import job_service
    original = job_service.generate_certificate_for_recipient

    def fail_once(session, job, recipient):
        if recipient.email == "bob@example.com":
            raise RuntimeError("simulated failure")
        return original(session, job, recipient)

    import app.services.job_service as js
    js.generate_certificate_for_recipient = fail_once
    try:
        with SessionLocal() as session:
            process_job(session, job_id)
    finally:
        js.generate_certificate_for_recipient = original

    job = client.get(f"/api/jobs/{job_id}/").json()
    assert job["status"] == "PARTIALLY_COMPLETED"
    assert job["successful_count"] == 1
    assert job["failed_count"] == 1
