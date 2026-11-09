"""Readable PDF and DOCX exports for structured MOMENT AI outputs."""
from __future__ import annotations

import json
import re
from io import BytesIO
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether,
)

LABELS = {
    "meeting_title": "Meeting title", "date": "Date", "attendees": "Attendees",
    "executive_summary": "Executive summary", "agenda": "Agenda",
    "discussion_points": "Discussion points", "decisions": "Decisions",
    "action_items": "Action items", "open_questions": "Open questions",
    "risks_and_dependencies": "Risks and dependencies", "follow_up_email": "Follow-up email",
    "title": "Title", "topic_summary": "Topic summary", "topic_wise_notes": "Topic-wise notes",
    "definitions": "Definitions", "formulas": "Formulas", "examples": "Examples",
    "key_takeaways": "Key takeaways", "revision_sheet": "Revision sheet",
    "practice_questions": "Practice questions", "source_evidence": "Source material",
    "task": "Task", "owner": "Owner", "deadline": "Deadline", "question": "Question",
    "decision": "Decision", "point": "Discussion point", "risk": "Risk",
    "evidence": "Evidence", "type": "Status",
}
OMIT_KEYS = {"evidence", "source_evidence"}


def _payload(body: str):
    """Parse model JSON when present; retain plain-text fallback."""
    candidate = body.strip()
    candidate = re.sub(r"^\`\`\`(?:json)?\\s*|\\s*\`\`\`$", "", candidate, flags=re.I)
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None
    except (TypeError, json.JSONDecodeError):
        return None


def _label(key: str) -> str:
    return LABELS.get(key, key.replace("_", " ").strip().capitalize())


def _plain(value) -> str:
    if value is None or value == "":
        return "Not specified"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    text = str(value).strip()
    if text.lower() == "unknown":
        return "Not available in source"
    return text


def _ordered_items(data: dict):
    preferred = [
        "meeting_title", "title", "date", "attendees", "executive_summary", "topic_summary",
        "agenda", "discussion_points", "decisions", "action_items", "topic_wise_notes",
        "definitions", "formulas", "examples", "key_takeaways", "revision_sheet",
        "practice_questions", "open_questions", "risks_and_dependencies", "follow_up_email",
        "source_evidence",
    ]
    keys = [key for key in preferred if key in data]
    keys.extend(key for key in data if key not in keys)
    return [(key, data[key]) for key in keys if key not in OMIT_KEYS]


def _add_docx_value(doc, key: str, value):
    if key == "action_items" and isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
        table = doc.add_table(rows=1, cols=3)
        table.style = "Light Shading Accent 1"
        for cell, heading in zip(table.rows[0].cells, ("Task", "Owner", "Deadline")):
            cell.text = heading
        for item in value:
            cells = table.add_row().cells
            cells[0].text = _plain(item.get("task"))
            cells[1].text = _plain(item.get("owner"))
            cells[2].text = _plain(item.get("deadline"))
            if item.get("evidence"):
                p = doc.add_paragraph()
                run = p.add_run("Evidence: " + _plain(item["evidence"]))
                run.italic = True
                run.font.size = Pt(8)
        return

    if isinstance(value, dict):
        for subkey, subvalue in value.items():
            p = doc.add_paragraph()
            run = p.add_run(str(subkey))
            run.bold = True
            if isinstance(subvalue, (list, dict)):
                _add_docx_value(doc, subkey, subvalue)
            else:
                p.add_run(": " + _plain(subvalue))
        return

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                main = next((item[k] for k in ("point", "decision", "question", "risk", "task") if item.get(k)), None)
                if main is not None:
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(_plain(main))
                    for subkey, subvalue in item.items():
                        if subkey not in {"point", "decision", "question", "risk", "task", "evidence"} and subvalue is not None:
                            p.add_run(f" — {_label(subkey)}: {_plain(subvalue)}")
                    if item.get("evidence"):
                        evidence = doc.add_paragraph()
                        r = evidence.add_run("Evidence: " + _plain(item["evidence"]))
                        r.italic = True
                        r.font.size = Pt(8)
                else:
                    p = doc.add_paragraph()
                    p.add_run("; ".join(f"{_label(k)}: {_plain(v)}" for k, v in item.items() if k != "evidence"))
            else:
                doc.add_paragraph(_plain(item), style="List Number" if key == "practice_questions" else "List Bullet")
        return

    doc.add_paragraph(_plain(value))


def _build_docx(title: str, body: str) -> BytesIO:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10)
    normal.font.color.rgb = RGBColor(45, 55, 65)

    heading = doc.add_heading(title, level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading.runs[0].font.color.rgb = RGBColor(26, 71, 92)

    data = _payload(body)
    if data is None:
        for block in body.splitlines():
            if block.strip():
                doc.add_paragraph(block.strip())
    else:
        for key, value in _ordered_items(data):
            if value is None or value == [] or value == "":
                continue
            doc.add_heading(_label(key), level=1)
            _add_docx_value(doc, key, value)

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output


def _build_pdf(title: str, body: str) -> BytesIO:
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MomentTitle", parent=base["Title"], alignment=TA_CENTER,
        textColor=colors.HexColor("#1A475C"), fontSize=20, leading=24, spaceAfter=16,
    )
    section_style = ParagraphStyle(
        "MomentSection", parent=base["Heading2"], textColor=colors.HexColor("#1A475C"),
        fontSize=12, leading=15, spaceBefore=12, spaceAfter=6, keepWithNext=True,
    )
    body_style = ParagraphStyle("MomentBody", parent=base["BodyText"], fontSize=9.5, leading=14, spaceAfter=5)
    small_style = ParagraphStyle("MomentSmall", parent=body_style, fontSize=8, textColor=colors.HexColor("#66727D"))

    def para(value, style=body_style):
        return Paragraph(escape(_plain(value)).replace("\n", "<br/>"), style)

    story = [Paragraph(escape(title), title_style)]
    data = _payload(body)
    if data is None:
        for block in body.splitlines():
            if block.strip():
                story.append(para(block.strip()))
        document.build(story)
        output.seek(0)
        return output

    for key, value in _ordered_items(data):
        if value is None or value == [] or value == "":
            continue
        story.append(Paragraph(escape(_label(key)), section_style))
        if key == "action_items" and isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            rows = [[para("Task"), para("Owner"), para("Deadline")]]
            for item in value:
                rows.append([para(item.get("task")), para(item.get("owner")), para(item.get("deadline"))])
            table = Table(rows, colWidths=[88 * mm, 35 * mm, 40 * mm], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F0F3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A475C")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D4DDE2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
            continue
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                story.append(para(f"{subkey}: {_plain(subvalue)}"))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    main_key = next((k for k in ("point", "decision", "question", "risk", "task") if item.get(k)), None)
                    if main_key:
                        story.append(para("• " + _plain(item[main_key])))
                        for subkey, subvalue in item.items():
                            if subkey not in {"point", "decision", "question", "risk", "task"} and subvalue is not None:
                                story.append(para(f"   {_label(subkey)}: {_plain(subvalue)}", small_style))
                    else:
                        story.append(para(" • ".join(f"{_label(k)}: {_plain(v)}" for k, v in item.items())))
                else:
                    story.append(para(("• " if key != "practice_questions" else "– ") + _plain(item)))
        else:
            story.append(para(value))

    document.build(story)
    output.seek(0)
    return output


def to_docx(title: str, body: str) -> BytesIO:
    """Create a formatted, editable DOCX document in memory."""
    return _build_docx(title, body)


def to_pdf(title: str, body: str) -> BytesIO:
    """Create a formatted PDF document in memory."""
    return _build_pdf(title, body)
