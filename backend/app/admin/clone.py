"""Build a draft copy of a service and its checklist. No database calls."""

from typing import Any

DRAFT_PREFIX = "DRAFT – verify against the official e-Sevai portal."
_DOC_FIELDS = (
    "code",
    "name_en",
    "name_ta",
    "description",
    "is_mandatory",
    "accepted_formats",
    "max_size_mb",
    "validity_days",
    "keywords",
    "required_fields",
    "rules",
    "sort_order",
    "is_active",
)


def build_clone_payload(
    service_row: dict[str, Any],
    required_docs: list[dict[str, Any]],
    new_slug: str,
    new_name_en: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Copy a service without ids or timestamps. The clone is always a draft."""
    description = str(service_row.get("description") or "").strip()
    if not description.startswith("DRAFT"):
        description = f"{DRAFT_PREFIX} {description}".strip() if description else DRAFT_PREFIX
    service_payload = {
        "slug": new_slug,
        "name_en": new_name_en,
        "name_ta": service_row.get("name_ta"),
        "description": description,
        "is_active": False,
        "is_verified": False,
    }
    doc_payloads = [{key: row.get(key) for key in _DOC_FIELDS} for row in required_docs]
    return service_payload, doc_payloads
