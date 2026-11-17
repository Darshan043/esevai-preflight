"""Run every configured check for one application.

The engine does not talk to the database. Pass the rows in, get results out.
"""

from datetime import date, datetime, timezone

from app.validation.checks import date_validity, document_type, id_number_format, image_quality, required_fields
from app.validation.cross_checks import check_missing_documents, check_name_consistency
from app.validation.models import DocumentInput, Result

_RANK = {"fail": 0, "warning": 1, "pass": 2}


def validate_application(
    required_docs: list[dict[str, object]],
    uploaded_docs: list[DocumentInput],
    today: date | None = None,
) -> list[Result]:
    """Check processed files, then missing slots and name consistency."""
    current = today or datetime.now(timezone.utc).date()
    results: list[Result] = []
    for document in uploaded_docs:
        results.extend(_one_document(document, current))
    results.extend(check_missing_documents(required_docs, uploaded_docs))
    names = check_name_consistency(uploaded_docs)
    if names is not None:
        results.append(names)
    results.sort(key=lambda item: (0 if item.uploaded_document_id is None else 1, item.sort_order, _RANK[item.status], item.check_code))
    return results


def _one_document(document: DocumentInput, today: date) -> list[Result]:
    order = document.config.get("sort_order")
    sort_order = int(order) if isinstance(order, int) else 0
    if document.status in {"uploaded", "processing"}:
        return [_tag(_not_processed(), document.document_id, sort_order)]
    if document.status == "failed":
        return [_tag(_unreadable(), document.document_id, sort_order)]
    if document.status != "processed":
        return [_tag(_not_processed(), document.document_id, sort_order)]

    found: list[Result] = []
    quality = image_quality(document)
    if quality is not None:
        found.append(quality)
    kind = document_type(document)
    if kind is not None:
        found.append(kind)
    found.extend(required_fields(document))
    number = id_number_format(document)
    if number is not None:
        found.append(number)
    dated = date_validity(document, today)
    if dated is not None:
        found.append(dated)
    return [_tag(item, document.document_id, sort_order) for item in found]


def _tag(result: Result, document_id: str, sort_order: int) -> Result:
    result.uploaded_document_id = document_id
    result.sort_order = sort_order
    return result


def _not_processed() -> Result:
    return Result(
        check_code="document_not_processed",
        check_name="Reading",
        status="warning",
        message="This document is still being read.",
        fix_suggestion="Wait for the reading to finish, then press Re-run checks.",
        details={"processed": False},
    )


def _unreadable() -> Result:
    return Result(
        check_code="document_unreadable",
        check_name="Reading",
        status="fail",
        message="We could not read this file.",
        fix_suggestion="Upload a clearer photo or a different file.",
        details={"readable": False},
    )
