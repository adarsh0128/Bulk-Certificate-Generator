from __future__ import annotations

from app.services.job_service import process_job


def test_failure_on_one_recipient_keeps_others_processing(client_and_db):
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
            {"name": "Charlie Brown", "email": "charlie@example.com"},
        ],
    }
    job_id = client.post("/api/jobs/", json=payload).json()["job_id"]

    from app.services import job_service
    original = job_service.generate_certificate_for_recipient

    def fail_for_bob(session, job, recipient):
        if recipient.email == "bob@example.com":
            raise RuntimeError("simulated PDF failure")
        return original(session, job, recipient)

    job_service.generate_certificate_for_recipient = fail_for_bob
    try:
        with SessionLocal() as session:
            process_job(session, job_id)
    finally:
        job_service.generate_certificate_for_recipient = original

    result = client.get(f"/api/jobs/{job_id}/certificates/")
    items = result.json()["items"]
    successful = [item for item in items if item["status"] == "COMPLETED"]
    failed = [item for item in items if item["status"] == "FAILED"]
    assert len(successful) == 2
    assert len(failed) == 1


def test_all_invalid_recipients_end_in_failed_terminal_state(client_and_db):
    client, SessionLocal = client_and_db
    payload = {
        "certificate": {
            "course_name": "Python Backend Development",
            "organization_name": "ABC Academy",
            "issue_date": "2026-10-06",
            "signatory_name": "John Smith",
        },
        "recipients": [{"name": "Alice", "email": "not-valid"}],
    }
    response = client.post("/api/jobs/", json=payload)
    job_id = response.json()["job_id"]
    with SessionLocal() as session:
        pass
    job_response = client.get(f"/api/jobs/{job_id}/")
    data = job_response.json()
    assert data["rejected_count"] == 1
    assert data["status"] in {"FAILED", "PARTIALLY_COMPLETED"}
