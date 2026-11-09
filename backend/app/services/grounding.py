"""Conservative validation for corporate meeting outputs."""
from __future__ import annotations

import json
import re
from typing import Any


CORPORATE_KEYS = {
    "meeting_title", "date", "attendees", "executive_summary", "agenda",
    "discussion_points", "decisions", "action_items", "open_questions",
    "risks_and_dependencies", "follow_up_email",
}


def _normalise(value: Any) -> str:
    """Normalise text for evidence matching while preserving token order."""
    return " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _is_supported(value: Any, source: str) -> bool:
    needle = _normalise(value)
    haystack = _normalise(source)
    return bool(needle) and needle in haystack


def _evidence_is_valid(item: dict[str, Any], source: str, fields: tuple[str, ...]) -> bool:
    evidence = item.get("evidence")
    if not isinstance(evidence, str) or not _is_supported(evidence, source):
        return False
    return all(
        item.get(field) is None or item.get(field) == ""
        or _is_supported(item[field], evidence)
        for field in fields
    )


def _parse_json(generated: str) -> dict[str, Any]:
    candidate = generated.strip()
    fence = chr(96) * 3
    if candidate.startswith(fence):
        candidate = candidate[len(fence):]
        if candidate[:4].lower() == "json":
            candidate = candidate[4:]
        if candidate.endswith(fence):
            candidate = candidate[:-len(fence)]
        candidate = candidate.strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("The AI returned invalid JSON. Please retry generation.") from exc
    if not isinstance(value, dict):
        raise ValueError("The AI response must be a JSON object. Please retry generation.")
    return value


def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _email_from_validated_minutes(data: dict[str, Any]) -> str:
    """Build email only from fields that have passed source validation."""
    title = data.get("meeting_title")
    subject = f"Follow-up: {title}" if isinstance(title, str) and title else "Meeting follow-up"
    lines = [f"Subject: {subject}", "", "Hi everyone,", "", "Here is the meeting recap."]
    decisions = data["decisions"]
    actions = data["action_items"]
    if decisions:
        lines.extend(["", "Confirmed decisions:"])
        for item in decisions:
            lines.append(f"- {item['description']}")
    if actions:
        lines.extend(["", "Action items:"])
        for item in actions:
            task = item["task"]
            owner = item.get("owner")
            deadline = item.get("deadline")
            detail = f"- {task}"
            if owner:
                detail += f" — Owner: {owner}"
            if deadline:
                detail += f" — Deadline: {deadline}"
            lines.append(detail)
    if not decisions and not actions:
        lines.extend(["", "No confirmed decisions or assigned action items were recorded in the supplied source."])
    lines.extend(["", "Please review and correct anything that does not match the meeting.", "", "Regards,"])
    return "\n".join(lines)


def validate_corporate_output(generated: str, source_text: str) -> str:
    """Remove unsupported claims and create a deterministic, grounded email."""
    data = _parse_json(generated)
    for key in CORPORATE_KEYS:
        if key not in data:
            data[key] = [] if key in {
                "attendees", "agenda", "discussion_points", "decisions",
                "action_items", "open_questions", "risks_and_dependencies",
            } else None

    if data.get("meeting_title") and not _is_supported(data["meeting_title"], source_text):
        data["meeting_title"] = None
    if data.get("date") and not _is_supported(data["date"], source_text):
        data["date"] = None

    data["agenda"] = [
        item for item in _safe_list(data["agenda"])
        if isinstance(item, dict)
        and isinstance(item.get("item"), str)
        and _evidence_is_valid(item, source_text, ("item",))
    ]
    for item in data["agenda"]:
        item.pop("evidence", None)

    data["discussion_points"] = [
        item for item in _safe_list(data["discussion_points"])
        if isinstance(item, dict)
        and isinstance(item.get("summary"), str)
        and _evidence_is_valid(item, source_text, ("summary",))
    ]
    data["executive_summary"] = " ".join(
        item["summary"] for item in data["discussion_points"]
    ) or "No source-supported discussion summary could be extracted."

    data["attendees"] = [
        item for item in _safe_list(data["attendees"])
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and _is_supported(item["name"], source_text)
    ]
    for attendee in data["attendees"]:
        role = attendee.get("role")
        if role and not _is_supported(role, source_text):
            attendee["role"] = None

    data["decisions"] = [
        item for item in _safe_list(data["decisions"])
        if isinstance(item, dict)
        and isinstance(item.get("description"), str)
        and _evidence_is_valid(item, source_text, ("description",))
    ]
    data["action_items"] = [
        item for item in _safe_list(data["action_items"])
        if isinstance(item, dict)
        and isinstance(item.get("task"), str)
        and _evidence_is_valid(item, source_text, ("task", "owner", "deadline"))
    ]
    data["open_questions"] = [
        item for item in _safe_list(data["open_questions"])
        if isinstance(item, dict)
        and isinstance(item.get("question"), str)
        and "?" in str(item.get("evidence", ""))
        and _evidence_is_valid(item, source_text, ("question",))
    ]
    data["risks_and_dependencies"] = [
        item for item in _safe_list(data["risks_and_dependencies"])
        if isinstance(item, dict)
        and isinstance(item.get("description"), str)
        and _evidence_is_valid(item, source_text, ("description",))
    ]

    for key in ("discussion_points", "decisions", "action_items", "open_questions", "risks_and_dependencies"):
        for item in data[key]:
            item.pop("evidence", None)

    data["follow_up_email"] = _email_from_validated_minutes(data)
    return json.dumps(data, ensure_ascii=False, indent=2)
