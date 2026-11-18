"""Rewrite saved check messages into short citizen-friendly sentences.

Only check codes, statuses, short messages, and document names are sent.
"""

import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_MARKUP = re.compile(r"<[^>]{0,200}>")
_ALLOWED = ("id", "document_name", "check_code", "status", "message", "fix_suggestion")


class ExplanationParseError(Exception):
    """The model reply was not the explanation JSON we asked for."""


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(max_length=80)
    explanation: str = Field(max_length=220)


class _Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_Item]
    overall_tip: str | None = Field(default=None, max_length=240)


def build_explanation_prompt(items: list[dict[str, object]], language: str) -> tuple[str, str]:
    """Build a prompt from non-passing checks. Pass rows are left out."""
    language_name = "Tamil" if language == "ta" else "English"
    system = (
        "You help a citizen who has limited technical knowledge. "
        "For each check, write one or two short sentences: what is wrong and what to do. "
        "Be polite. Do not make legal or official claims. Do not make guarantees. Do not include URLs. "
        f"Write in simple {language_name}. "
        'Output ONLY JSON of the form {"items":[{"id":"...","explanation":"..."}],"overall_tip":"..."}. '
        "Use only the ids you were given. explanation is at most 220 characters. "
        "overall_tip is at most 240 characters."
    )
    lines: list[str] = []
    kept = 0
    for item in items:
        if kept >= 25:
            break
        status = str(item.get("status") or "")
        if status == "pass":
            continue
        safe = {key: _clip(item.get(key)) for key in _ALLOWED}
        if not safe["id"]:
            continue
        lines.append(
            f"id: {safe['id']}; document: {safe['document_name'] or 'Application'}; "
            f"check: {safe['check_code']}; status: {safe['status']}; "
            f"message: {safe['message']}; suggestion: {safe['fix_suggestion']}"
        )
        kept += 1
    body = "\n".join(lines).replace("</check_items>", " ")
    user = f"Language: {language_name}\n<check_items>\n{body}\n</check_items>"
    return system, user


def parse_explanations(raw_text: str, valid_ids: set[str]) -> dict[str, object]:
    """Keep only ids from the list. A bad reply raises ExplanationParseError."""
    payload = _json_object(raw_text)
    try:
        parsed = _Reply.model_validate(payload)
    except ValidationError as exc:
        raise ExplanationParseError from exc
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for item in parsed.items:
        if item.id not in valid_ids or item.id in seen:
            raise ExplanationParseError
        seen.add(item.id)
        explanation = _plain(item.explanation)
        if not explanation or len(explanation) > 220:
            raise ExplanationParseError
        items.append({"id": item.id, "explanation": explanation})
    tip = _plain(parsed.overall_tip or "")
    if tip and len(tip) > 240:
        raise ExplanationParseError
    return {"items": items, "overall_tip": tip or None}


def _json_object(raw_text: str) -> dict[str, object]:
    start = raw_text.find("{")
    if start < 0:
        raise ExplanationParseError
    try:
        value, _end = json.JSONDecoder().raw_decode(raw_text[start:])
    except json.JSONDecodeError as exc:
        raise ExplanationParseError from exc
    if not isinstance(value, dict):
        raise ExplanationParseError
    return value


def _clip(value: object) -> str:
    text = _plain(str(value or ""))
    return text[:300]


def _plain(value: str) -> str:
    text = _URL.sub(" ", value)
    text = _MARKUP.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()
