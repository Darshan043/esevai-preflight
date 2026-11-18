"""Read trusted AI fields. Low confidence and an empty record are ignored."""

from datetime import date

from app.validation.models import DocumentInput
from app.validation.text_extract import _normalise_name, extract_name_candidate


def trusted_fields(document: DocumentInput) -> dict[str, object] | None:
    """High or medium confidence fields. Anything else returns None."""
    fields = document.extracted_fields
    if not isinstance(fields, dict) or not fields:
        return None
    if fields.get("extraction_confidence") not in {"high", "medium"}:
        return None
    return fields


def comparable_name(document: DocumentInput) -> str:
    """Use the AI name when it is trusted. Otherwise use the OCR guess."""
    fields = trusted_fields(document)
    if fields is None:
        return extract_name_candidate(document.ocr_text_masked) or ""
    raw = fields.get("holder_name")
    if not isinstance(raw, str):
        return ""
    return _normalise_name(raw)


def ai_name_present(document: DocumentInput) -> bool | None:
    """True or false when AI is trusted. None means the caller should use OCR."""
    fields = trusted_fields(document)
    if fields is None:
        return None
    raw = fields.get("holder_name")
    if isinstance(raw, str) and _normalise_name(raw):
        return True
    return None


def ai_date_present(document: DocumentInput) -> bool | None:
    """True when a trusted AI date exists. None means the caller should use OCR."""
    fields = trusted_fields(document)
    if fields is None:
        return None
    if any(iso_date(fields.get(key)) is not None for key in ("date_of_birth", "issue_date", "expiry_date")):
        return True
    return None


def iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
