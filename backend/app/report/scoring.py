"""Turn saved check results into a score and a label.

These functions do not talk to the database or to the AI. They only look at
the check rows you pass in, so the same inputs always give the same score.
"""

from typing import Any

# --- Tunable constants (change these numbers to make scoring stricter or kinder) ---
FAIL_PENALTY = 40  # Points taken off one document for each of its fail results.
WARNING_PENALTY = 10  # Points taken off one document for each of its warning results.
CROSS_FAIL_PENALTY = 15  # Points taken off the overall score for each application-level fail.
CROSS_WARNING_PENALTY = 5  # Points taken off the overall score for each application-level warning.
MANDATORY_WEIGHT = 2  # How much a mandatory document counts in the average.
OPTIONAL_WEIGHT = 1  # How much an optional document counts in the average.
READY_MIN_SCORE = 85  # Lowest overall score that can still be labelled "ready".
ALMOST_READY_MIN_SCORE = 60  # Lowest overall score that can still be labelled "almost_ready".
# Missing-document rows are already a 0 on that slot, so they are not also a cross penalty.
MISSING_CHECK_CODE = "missing_document"
# -----------------------------------------------------------------------------------


def _status(item: Any) -> str:
    """Read status from a dict (database row) or a Result object."""
    if isinstance(item, dict):
        return str(item.get("status") or "")
    return str(getattr(item, "status", "") or "")


def _check_code(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("check_code") or "")
    return str(getattr(item, "check_code", "") or "")


def _upload_id(item: Any) -> str | None:
    if isinstance(item, dict):
        value = item.get("uploaded_document_id")
    else:
        value = getattr(item, "uploaded_document_id", None)
    if value is None or value == "":
        return None
    return str(value)


def _flag(value: Any) -> bool:
    return value is True or value == "true"


def score_one_document(
    *,
    is_mandatory: bool,
    uploaded: bool,
    fail_count: int,
    warning_count: int,
) -> int | None:
    """Score one checklist slot from 0 to 100, or None if it is skipped.

    A missing optional document is left out of the average, so it returns None.
    A missing mandatory document scores 0. The endpoint refuses documents that
    are still being read, so this function always scores an uploaded file.
    """
    if not uploaded:
        return 0 if is_mandatory else None
    points = 100 - FAIL_PENALTY * fail_count - WARNING_PENALTY * warning_count
    return max(0, points)


def overall_score(document_scores: list[tuple[int, int]], cross_fail: int, cross_warning: int) -> int:
    """Weighted average of document scores, minus cross-document penalties."""
    if document_scores:
        total = sum(score * weight for score, weight in document_scores)
        weight_sum = sum(weight for _score, weight in document_scores)
        average = total / weight_sum
    else:
        average = 0.0
    penalty = CROSS_FAIL_PENALTY * cross_fail + CROSS_WARNING_PENALTY * cross_warning
    return min(100, max(0, int(round(average - penalty))))


def readiness_label(*, score: int, fail_count: int, missing_mandatory: int) -> str:
    """Pick ready / almost_ready / not_ready. A fail or a missing slot blocks ready."""
    if fail_count == 0 and missing_mandatory == 0 and score >= READY_MIN_SCORE:
        return "ready"
    if missing_mandatory == 0 and fail_count <= 2 and score >= ALMOST_READY_MIN_SCORE:
        return "almost_ready"
    return "not_ready"


def _results_for_upload(results: list[Any], upload_id: str) -> list[Any]:
    return [item for item in results if _upload_id(item) == upload_id]


def _is_cross_penalty(item: Any) -> bool:
    """Application-level fail/warning that is not the missing-document row."""
    if _upload_id(item) is not None:
        return False
    if _check_code(item) == MISSING_CHECK_CODE:
        return False
    return _status(item) in {"fail", "warning"}


def compute_readiness(
    required_docs: list[dict[str, Any]],
    uploaded_docs: list[dict[str, Any]],
    validation_results: list[Any],
) -> dict[str, Any]:
    """Return overall score, label, and a score for each required document id.

    The document_scores map uses None for an optional slot with no file.
    """
    uploads_by_required = {
        str(row.get("required_document_id") or ""): row for row in uploaded_docs if row.get("required_document_id")
    }
    document_scores: dict[str, int | None] = {}
    weighted: list[tuple[int, int]] = []
    missing_mandatory = 0

    for required in required_docs:
        required_id = str(required.get("id") or "")
        if not required_id or required.get("is_active") is False:
            continue
        mandatory = _flag(required.get("is_mandatory"))
        upload = uploads_by_required.get(required_id)
        uploaded = upload is not None
        if mandatory and not uploaded:
            missing_mandatory += 1
        upload_id = str(upload.get("id") or "") if upload else ""
        owned = _results_for_upload(validation_results, upload_id) if upload_id else []
        fail_count = sum(1 for item in owned if _status(item) == "fail")
        warning_count = sum(1 for item in owned if _status(item) == "warning")
        score = score_one_document(
            is_mandatory=mandatory,
            uploaded=uploaded,
            fail_count=fail_count,
            warning_count=warning_count,
        )
        document_scores[required_id] = score
        if score is None:
            continue
        weight = MANDATORY_WEIGHT if mandatory else OPTIONAL_WEIGHT
        weighted.append((score, weight))

    cross_fail = sum(1 for item in validation_results if _is_cross_penalty(item) and _status(item) == "fail")
    cross_warning = sum(1 for item in validation_results if _is_cross_penalty(item) and _status(item) == "warning")
    score = overall_score(weighted, cross_fail, cross_warning)
    fail_count = sum(1 for item in validation_results if _status(item) == "fail")
    label = readiness_label(score=score, fail_count=fail_count, missing_mandatory=missing_mandatory)
    return {
        "score": score,
        "label": label,
        "document_scores": document_scores,
        "missing_mandatory": missing_mandatory,
        "fail_count": fail_count,
    }
