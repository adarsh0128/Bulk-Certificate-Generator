from __future__ import annotations

from app.db.models.job import JobStatus
from app.db.models.recipient import RecipientStatus
from app.services.job_service import process_job


def build_payload(valid=True):
    if not valid:
        return {
            "certificate": {
                "course_name": "Python Backend Development",
                "organization_name": "ABC Academy",
                "issue_date": "2026-10-06",
                "signatory_name": "John Smith",
            },
            "recipients": [{"name": "Charlie Brown", "email": "invalid-email"}],
        }
    return {
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


def test_create_generation_job(client_and_db):
    client, _ = client_and_db
    response = client.post("/api/jobs/", json=build_payload())
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "PENDING"
    assert payload["job_id"]


def test_reject_structurally_invalid_request(client_and_db):
    client, _ = client_and_db
    malformed = {"certificate": {}, "recipients": []}
    response = client.post("/api/jobs/", json=malformed)
    assert response.status_code == 422


def test_reject_invalid_recipient_data(client_and_db):
    client, _ = client_and_db
    response = client.post("/api/jobs/", json=build_payload(valid=False))
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job_response = client.get(f"/api/jobs/{job_id}/")
    assert job_response.status_code == 200
    certificates = client.get(f"/api/jobs/{job_id}/certificates/")
    data = certificates.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "REJECTED"


def test_enforce_max_recipients_per_job(client_and_db):
    client, _ = client_and_db
    payload = {
        "certificate": {
            "course_name": "Python Backend Development",
            "organization_name": "ABC Academy",
            "issue_date": "2026-10-06",
            "signatory_name": "John Smith",
        },
        "recipients": [{"name": f"Person {idx}", "email": f"person{idx}@example.com"} for idx in range(1001)],
    }
    response = client.post("/api/jobs/", json=payload)
    assert response.status_code == 422


def test_duplicate_email_rejected_within_same_job(client_and_db):
    client, _ = client_and_db
    payload = {
        "certificate": {
            "course_name": "Python Backend Development",
            "organization_name": "ABC Academy",
            "issue_date": "2026-10-06",
            "signatory_name": "John Smith",
        },
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Williams", "email": "bob@example.com"},
        ],
    }
    response = client.post("/api/jobs/", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = client.get(f"/api/jobs/{job_id}/certificates/")
    statuses = [item["status"] for item in result.json()["items"]]
    assert statuses.count("REJECTED") >= 1
    assert statuses.count("PENDING") >= 1


def test_successful_pdf_generation(client_and_db):
    client, SessionLocal = client_and_db
    payload = build_payload()
    create_response = client.post("/api/jobs/", json=payload)
    job_id = create_response.json()["job_id"]

    with SessionLocal() as session:
        process_job(session, job_id)

    status_response = client.get(f"/api/jobs/{job_id}/")
    body = status_response.json()
    assert body["status"] == JobStatus.COMPLETED.value
    assert body["successful_count"] == 2
    assert body["failed_count"] == 0

    cert_list = client.get(f"/api/jobs/{job_id}/certificates/")
    items = cert_list.json()["items"]
    assert len(items) == 2
    assert all(item["certificate_id"] for item in items)
    assert all(item["download_url"] for item in items)


def test_get_unknown_job_returns_404(client_and_db):
    client, _ = client_and_db
    response = client.get("/api/jobs/unknown-job/")
    assert response.status_code == 404


def test_get_unknown_certificate_returns_404(client_and_db):
    client, _ = client_and_db
    response = client.get("/api/certificates/unknown-cert/")
    assert response.status_code == 404


def test_empty_or_entirely_invalid_recipient_list(client_and_db):
    client, _ = client_and_db
    empty_payload = {"certificate": {"course_name": "Course", "organization_name": "Org", "issue_date": "2026-10-06", "signatory_name": "A"}, "recipients": []}
    assert client.post("/api/jobs/", json=empty_payload).status_code == 422

    invalid_payload = {
        "certificate": {"course_name": "Course", "organization_name": "Org", "issue_date": "2026-10-06", "signatory_name": "A"},
        "recipients": [{"name": "Person", "email": "bad-email"}],
    }
    response = client.post("/api/jobs/", json=invalid_payload)
    assert response.status_code == 202


def test_job_counts_and_recipient_statuses_stay_consistent(client_and_db):
    client, SessionLocal = client_and_db
    payload = build_payload()
    response = client.post("/api/jobs/", json=payload)
    job_id = response.json()["job_id"]
    with SessionLocal() as session:
        process_job(session, job_id)
    body = client.get(f"/api/jobs/{job_id}/").json()
    assert body["total_count"] == 2
    assert body["pending_count"] == 0
    assert body["processing_count"] == 0
    assert body["successful_count"] == 2
    assert body["failed_count"] == 0
    assert body["rejected_count"] == 0
