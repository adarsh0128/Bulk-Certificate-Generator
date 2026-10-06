from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from app.services.pdf_generator import generate_certificate_pdf


def test_generate_certificate_pdf_creates_valid_non_empty_file(tmp_path):
    output_path = tmp_path / "certificates" / "example.pdf"
    generate_certificate_pdf(
        output_path,
        organization_name="ABC Academy",
        course_name="Python Backend Development",
        recipient_name="Alice Johnson",
        issue_date="2026-10-06",
        signatory_name="John Smith",
        certificate_id="cert-123",
    )
    assert output_path.exists()
    assert output_path.stat().st_size > 1000

    with open(output_path, "rb") as handle:
        content = handle.read(5)
        assert content.startswith(b"%PDF")
