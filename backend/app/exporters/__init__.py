"""PDF and DOCX export helpers for MOMENT AI."""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def to_docx(title: str, body: str) -> BytesIO:
    """Create an editable DOCX document in memory."""
    doc = Document()
    doc.add_heading(title, level=0)
    for block in body.split("\n"):
        if block.strip():
            doc.add_paragraph(block)
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output


def to_pdf(title: str, body: str) -> BytesIO:
    """Create a PDF document in memory."""
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 14)]
    for block in body.split("\n"):
        if block.strip():
            story.append(Paragraph(escape(block), styles["BodyText"]))
            story.append(Spacer(1, 8))
    document.build(story)
    output.seek(0)
    return output
