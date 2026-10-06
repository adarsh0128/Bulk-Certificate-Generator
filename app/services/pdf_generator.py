from __future__ import annotations

import textwrap
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def generate_certificate_pdf(output_path: Path, *, organization_name: str, course_name: str, recipient_name: str, issue_date: str, signatory_name: str, certificate_id: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(A4)
    pdf_canvas = canvas.Canvas(str(output_path), pagesize=landscape(A4))
    pdf_canvas.setTitle(f"Certificate - {recipient_name}")

    page_margin = 45
    border_color = HexColor("#1F2937")
    accent_color = HexColor("#2563EB")
    text_color = HexColor("#111827")
    muted_color = HexColor("#475569")

    pdf_canvas.setStrokeColor(border_color)
    pdf_canvas.setLineWidth(2)
    pdf_canvas.rect(page_margin, page_margin, width - 2 * page_margin, height - 2 * page_margin)

    pdf_canvas.setStrokeColor(accent_color)
    pdf_canvas.setLineWidth(1.2)
    pdf_canvas.roundRect(page_margin + 18, page_margin + 18, width - 2 * (page_margin + 18), height - 2 * (page_margin + 18), 18, stroke=1, fill=0)

    pdf_canvas.setFillColor(text_color)
    pdf_canvas.setFont("Helvetica-Bold", 24)
    pdf_canvas.drawCentredString(width / 2, height - 85, organization_name)

    pdf_canvas.setFillColor(accent_color)
    pdf_canvas.setFont("Helvetica-Bold", 28)
    pdf_canvas.drawCentredString(width / 2, height - 140, "Certificate of Completion")

    pdf_canvas.setFillColor(muted_color)
    pdf_canvas.setFont("Helvetica", 15)
    pdf_canvas.drawCentredString(width / 2, height - 185, "This is to certify that")

    pdf_canvas.setFillColor(text_color)
    pdf_canvas.setFont("Helvetica-Bold", 26)
    wrapped_name = textwrap.fill(recipient_name, width=28)
    pdf_canvas.drawCentredString(width / 2, height - 250, wrapped_name.splitlines()[0])
    if len(wrapped_name.splitlines()) > 1:
        pdf_canvas.drawCentredString(width / 2, height - 290, wrapped_name.splitlines()[1])

    pdf_canvas.setFillColor(muted_color)
    pdf_canvas.setFont("Helvetica", 16)
    course_lines = textwrap.wrap(course_name, width=48)
    if course_lines:
        course_first = course_lines[0]
        pdf_canvas.drawCentredString(width / 2, height - 345, f"has successfully completed the course: {course_first}")
    if len(course_lines) > 1:
        pdf_canvas.drawCentredString(width / 2, height - 375, " ".join(course_lines[1:]))

    pdf_canvas.setFillColor(text_color)
    pdf_canvas.setFont("Helvetica", 15)
    pdf_canvas.drawCentredString(width / 2, height - 430, f"Issued on {issue_date}")

    pdf_canvas.setFillColor(muted_color)
    pdf_canvas.setFont("Helvetica-Bold", 12)
    pdf_canvas.drawCentredString(width / 2, height - 545, "Certificate ID")
    pdf_canvas.setFont("Helvetica", 11)
    pdf_canvas.drawCentredString(width / 2, height - 565, certificate_id)

    signature_y = 120
    pdf_canvas.setStrokeColor(border_color)
    pdf_canvas.line(width / 2 - 120, signature_y + 40, width / 2 + 120, signature_y + 40)
    pdf_canvas.setFillColor(text_color)
    pdf_canvas.setFont("Helvetica-Bold", 14)
    pdf_canvas.drawCentredString(width / 2, signature_y + 15, signatory_name)
    pdf_canvas.setFont("Helvetica", 11)
    pdf_canvas.drawCentredString(width / 2, signature_y - 5, "Authorized Signatory")

    pdf_canvas.save()
