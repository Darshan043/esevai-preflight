"""Checks that look across the checklist, not inside one file."""

from rapidfuzz import fuzz

from app.validation.ai_fields import comparable_name
from app.validation.defaults import NAME_MATCH_PASS, NAME_MATCH_WARN
from app.validation.models import DocumentInput, Result


def check_name_consistency(documents: list[DocumentInput]) -> Result | None:
    """Compare names only when the rules ask for it and a name was found.

    Fewer than two comparable documents is not a failure. Details contain
    document codes and scores, never the names themselves.
    """
    comparable: list[tuple[str, str]] = []
    for document in documents:
        if document.status != "processed":
            continue
        rules = document.config.get("rules")
        if not isinstance(rules, dict) or rules.get("check_name_match") is not True:
            continue
        name = comparable_name(document)
        code = str(document.config.get("code") or "")
        if name and code:
            comparable.append((code, name))
    if len(comparable) < 2:
        return None

    scores: list[dict[str, object]] = []
    worst = 100
    for index, (left_code, left_name) in enumerate(comparable):
        for right_code, right_name in comparable[index + 1 :]:
            score = int(round(fuzz.token_sort_ratio(left_name, right_name)))
            worst = min(worst, score)
            scores.append({"left_code": left_code, "right_code": right_code, "score": score})

    if worst < NAME_MATCH_WARN:
        status = "fail"
        message = "Names do not match across documents."
        fix = "Upload documents that all show the same person."
    elif worst < NAME_MATCH_PASS:
        status = "warning"
        message = "Names look slightly different across documents."
        fix = "Check that each document shows the same person's name."
    else:
        status = "pass"
        message = "The names match across the documents."
        fix = ""
    return Result(
        check_code="name_consistency",
        check_name="Name match",
        status=status,  # type: ignore[arg-type]
        message=message,
        fix_suggestion=fix,
        details={"scores": scores},
        uploaded_document_id=None,
        sort_order=10_000,
    )


def check_missing_documents(
    required_docs: list[dict[str, object]],
    uploaded_docs: list[DocumentInput],
) -> list[Result]:
    """A missing mandatory slot fails. A missing optional slot is ignored."""
    uploaded_ids = {str(item.config.get("id") or "") for item in uploaded_docs}
    results: list[Result] = []
    for config in required_docs:
        if config.get("is_active") is False:
            continue
        if config.get("is_mandatory") is not True:
            continue
        if str(config.get("id") or "") in uploaded_ids:
            continue
        code = str(config.get("code") or "")
        name = str(config.get("name_en") or "A required document")
        order = config.get("sort_order")
        results.append(
            Result(
                check_code="missing_document",
                check_name="Missing document",
                status="fail",
                message=f"{name} is missing.",
                fix_suggestion=f"Upload the {name}.",
                details={"required_document_code": code},
                uploaded_document_id=None,
                sort_order=int(order) if isinstance(order, int) else 0,
            )
        )
    return results
