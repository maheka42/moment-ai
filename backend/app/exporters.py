"""Document export helpers for MOMENT AI."""
from __future__ import annotations

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from xml.sax.saxutils import escape
from docx import Document


def to_docx(title: str, body: str) -> BytesIO:
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
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 14)]
    for block in body.split("\n"):
        if block.strip():
            story.append(Paragraph(escape(block), styles["BodyText"]))
            story.append(Spacer(1, 8))
    doc.build(story)
    output.seek(0)
    return output
