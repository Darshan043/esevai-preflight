"""Build the citizen-facing readiness report from already-saved check rows.

This module never calls Supabase or the AI. The score comes only from scoring.py.
"""

from datetime import datetime, timezone
from typing import Any
import re

from app.report.scoring import compute_readiness

# Strip long ID numbers and links in case a check message was saved incorrectly.
_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_DIGITS_16 = re.compile(r"\d{16}")
_DIGITS_12 = re.compile(r"\d{12}")

CARRY_TEXT = "Carry the ORIGINAL documents to the e-Sevai centre"
REMAINDER_TEXT = "Also review the remaining warnings"
MAX_NEXT_STEPS = 12


def sanitise_text(value: object) -> str:
    """Keep the wording, but drop 12-digit and 16-digit numbers and URLs."""
    text = value if isinstance(value, str) else ""
    text = _URL.sub("", text)
    text = _DIGITS_16.sub("", text)
    text = _DIGITS_12.sub("", text)
    return " ".join(text.split())


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    return {
        "check_code": getattr(item, "check_code", ""),
        "status": getattr(item, "status", ""),
        "message": getattr(item, "message", ""),
        "fix_suggestion": getattr(item, "fix_suggestion", ""),
        "uploaded_document_id": getattr(item, "uploaded_document_id", None),
    }


def _issue(item: Any) -> dict[str, str]:
    row = _as_dict(item)
    return {
        "check_code": str(row.get("check_code") or ""),
        "status": str(row.get("status") or ""),
        "message": sanitise_text(row.get("message")),
        "fix_suggestion": sanitise_text(row.get("fix_suggestion")),
    }


def _sort_key(required: dict[str, Any]) -> int:
    order = required.get("sort_order")
    return int(order) if isinstance(order, int) else 0


def _name(required: dict[str, Any]) -> str:
    return str(required.get("name_en") or required.get("code") or "This document")


def _code(required: dict[str, Any]) -> str:
    return str(required.get("code") or "")


def _upload_id(item: Any) -> str | None:
    row = _as_dict(item)
    value = row.get("uploaded_document_id")
    if value is None or value == "":
        return None
    return str(value)


def document_state(uploaded: bool, issues: list[dict[str, str]]) -> str:
    """missing, needs_fix, check_advised, or passed."""
    if not uploaded:
        return "missing"
    if any(issue["status"] == "fail" for issue in issues):
        return "needs_fix"
    if any(issue["status"] == "warning" for issue in issues):
        return "check_advised"
    return "passed"


def _step(priority: int, step_type: str, text: str, document_code: str | None) -> dict[str, Any]:
    return {
        "priority": priority,
        "type": step_type,
        "text": text,
        "document_code": document_code,
    }


def _action_text(name: str, issue: dict[str, str]) -> str:
    suggestion = issue.get("fix_suggestion") or ""
    message = issue.get("message") or ""
    detail = suggestion or message
    if name and detail:
        return f"{name}: {detail}"
    return detail or name


def _dedupe(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for step in steps:
        key = str(step.get("text") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(step)
    return unique


def build_next_steps(
    required_docs: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    application_issues: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Missing first, then document fails, application fails, warnings, then carry originals."""
    by_id = {str(item.get("required_document_id") or ""): item for item in documents}
    ordered = sorted(required_docs, key=_sort_key)
    draft: list[dict[str, Any]] = []

    for required in ordered:
        if required.get("is_active") is False:
            continue
        if required.get("is_mandatory") is not True:
            continue
        row = by_id.get(str(required.get("id") or ""))
        if row is None or row.get("state") != "missing":
            continue
        draft.append(_step(0, "missing", f"Get or upload: {_name(required)}", _code(required)))

    for required in ordered:
        row = by_id.get(str(required.get("id") or ""))
        if row is None:
            continue
        name = _name(required)
        code = _code(required)
        for issue in row.get("issues") or []:
            if issue.get("status") != "fail":
                continue
            draft.append(_step(0, "document_fail", _action_text(name, issue), code))

    for issue in application_issues:
        if issue.get("status") != "fail" or issue.get("check_code") == "missing_document":
            continue
        draft.append(_step(0, "application_fail", _action_text("", issue), None))

    for required in ordered:
        row = by_id.get(str(required.get("id") or ""))
        if row is None:
            continue
        name = _name(required)
        code = _code(required)
        for issue in row.get("issues") or []:
            if issue.get("status") != "warning":
                continue
            draft.append(_step(0, "warning", _action_text(name, issue), code))

    for issue in application_issues:
        if issue.get("status") != "warning":
            continue
        draft.append(_step(0, "warning", _action_text("", issue), None))

    unique = _dedupe(draft)
    carry = _step(0, "carry", CARRY_TEXT, None)
    room = MAX_NEXT_STEPS - 1
    if len(unique) > room:
        kept = unique[: room - 1]
        kept.append(_step(0, "warning", REMAINDER_TEXT, None))
        unique = kept
    unique.append(carry)
    return [{**step, "priority": index} for index, step in enumerate(unique, start=1)]


def _parse_stamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp


def is_report_current(generated_at: object, uploads: list[dict[str, Any]]) -> bool:
    """True when no file was uploaded, replaced, or re-read after the report time."""
    generated = _parse_stamp(generated_at)
    if generated is None:
        return False
    for upload in uploads:
        for key in ("updated_at", "created_at"):
            stamp = _parse_stamp(upload.get(key))
            if stamp is not None and stamp > generated:
                return False
    return True


def build_report(
    application: dict[str, Any],
    service: dict[str, Any],
    required_docs: list[dict[str, Any]],
    uploaded_docs: list[dict[str, Any]],
    validation_results: list[Any],
    now: datetime,
) -> dict[str, Any]:
    """Assemble the JSON object stored on applications.summary.report.

    service is accepted so callers can pass the loaded row. The report only
    keeps display names from required_docs, never storage paths or OCR text.
    """
    del application, service
    readiness = compute_readiness(required_docs, uploaded_docs, validation_results)
    scores: dict[str, int | None] = readiness["document_scores"]
    uploads_by_required = {
        str(row.get("required_document_id") or ""): row for row in uploaded_docs if row.get("required_document_id")
    }
    results_by_upload: dict[str, list[Any]] = {}
    application_rows: list[Any] = []
    for item in validation_results:
        upload_id = _upload_id(item)
        if upload_id is None:
            application_rows.append(item)
            continue
        results_by_upload.setdefault(upload_id, []).append(item)

    documents: list[dict[str, Any]] = []
    active = [row for row in required_docs if row.get("is_active") is not False]
    ordered = sorted(active, key=_sort_key)
    for required in ordered:
        required_id = str(required.get("id") or "")
        upload = uploads_by_required.get(required_id)
        owned = results_by_upload.get(str(upload.get("id") or ""), []) if upload else []
        issues = [_issue(item) for item in owned if _as_dict(item).get("status") != "pass"]
        uploaded = upload is not None
        documents.append(
            {
                "required_document_id": required_id,
                "code": _code(required),
                "name_en": sanitise_text(required.get("name_en") or _code(required)),
                "name_ta": sanitise_text(required.get("name_ta")) if required.get("name_ta") else None,
                "is_mandatory": required.get("is_mandatory") is True,
                "state": document_state(uploaded, issues),
                "score": scores.get(required_id),
                "issues": issues,
            }
        )

    application_issues = [
        _issue(item) for item in application_rows if _as_dict(item).get("status") != "pass"
    ]
    next_steps = build_next_steps(ordered, documents, application_issues)
    carry_list = [
        {
            "name_en": sanitise_text(required.get("name_en") or _code(required)),
            "name_ta": sanitise_text(required.get("name_ta")) if required.get("name_ta") else None,
            "is_mandatory": required.get("is_mandatory") is True,
        }
        for required in ordered
    ]
    statuses = [_as_dict(item).get("status") for item in validation_results]
    return {
        "generated_at": now.astimezone(timezone.utc).isoformat() if now.tzinfo else now.replace(tzinfo=timezone.utc).isoformat(),
        "score": readiness["score"],
        "label": readiness["label"],
        "counts": {
            "documents_required": len(ordered),
            "documents_uploaded": len(uploaded_docs),
            "mandatory_missing": readiness["missing_mandatory"],
            "pass": sum(1 for status in statuses if status == "pass"),
            "warning": sum(1 for status in statuses if status == "warning"),
            "fail": sum(1 for status in statuses if status == "fail"),
        },
        "documents": documents,
        "application_issues": application_issues,
        "next_steps": next_steps,
        "carry_list": carry_list,
    }
