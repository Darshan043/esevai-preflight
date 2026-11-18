"""One-document checks. Each check is skipped when its rule is not configured."""

import re
from datetime import date

from rapidfuzz import fuzz

from app.validation.defaults import (
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MAX_SKEW,
    DEFAULT_MIN_BLUR,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MIN_HEIGHT,
    DEFAULT_MIN_OCR_CONFIDENCE,
    DEFAULT_MIN_WIDTH,
    DEFAULT_MIN_WORDS,
    KEYWORD_MATCH,
)
from app.validation.ai_fields import ai_date_present, ai_name_present, iso_date, trusted_fields
from app.validation.models import DocumentInput, Result
from app.validation.text_extract import extract_dates, extract_name_candidate

_NUMBER = re.compile(r"(?<!\d)\d{6,}(?!\d)")


def image_quality(document: DocumentInput) -> Result | None:
    """Sharpness, size, light, blank page, tilt, and OCR confidence."""
    metrics = document.quality_metrics if isinstance(document.quality_metrics, dict) else {}
    photo = _is_photo(document.config)
    problems: list[tuple[str, str, str, str]] = []

    if metrics.get("is_probably_blank") is True:
        problems.append(("fail", "This page looks blank.", "Upload a photo of the document, not an empty page.", "blank"))

    blur = _number(metrics, "blur_score")
    min_blur = _rule_number(document.config, "min_blur_score", DEFAULT_MIN_BLUR)
    if blur is not None and blur < min_blur:
        problems.append(("fail", "This photo is too blurry.", "Hold the camera steady and take the photo again.", "blur_low"))

    width = _number(metrics, "width")
    height = _number(metrics, "height")
    min_width = _rule_number(document.config, "min_width", DEFAULT_MIN_WIDTH)
    min_height = _rule_number(document.config, "min_height", DEFAULT_MIN_HEIGHT)
    if (width is not None and width < min_width) or (height is not None and height < min_height):
        problems.append(("warning", "This photo is small.", "Move closer, or choose a higher-resolution photo.", "resolution_low"))

    brightness = _number(metrics, "brightness_mean")
    low = _rule_number(document.config, "min_brightness", DEFAULT_MIN_BRIGHTNESS)
    high = _rule_number(document.config, "max_brightness", DEFAULT_MAX_BRIGHTNESS)
    contrast = _number(metrics, "contrast_std")
    # White paper makes the average very high even when the letters are black.
    # Call it bad lighting only for a blank bright page, or for older metrics
    # that did not record contrast and so cannot be told apart from glare.
    glare = brightness is not None and brightness > high and (
        contrast is None or metrics.get("is_probably_blank") is True
    )
    if (brightness is not None and brightness < low) or glare:
        problems.append(("warning", "The lighting makes this hard to read.", "Take the photo again in even light.", "brightness_off"))

    skew = _number(metrics, "skew_angle_degrees")
    if skew is not None and abs(skew) > DEFAULT_MAX_SKEW:
        problems.append(("warning", "The page looks tilted.", "Lay the page flat and take the photo again.", "tilt_high"))

    # A photo slot has no words to read, so confidence is not a failure.
    confidence = _number(metrics, "ocr_mean_confidence")
    if not photo and confidence is not None and confidence < DEFAULT_MIN_OCR_CONFIDENCE:
        problems.append(("warning", "The words are hard to read.", "Upload a sharper photo with the whole page in frame.", "confidence_low"))

    status = "pass"
    message = "This photo looks clear enough."
    fix = ""
    if any(item[0] == "fail" for item in problems):
        status = "fail"
        message, fix = _first(problems, "fail")
    elif problems:
        status = "warning"
        message, fix = _first(problems, "warning")

    return Result(
        check_code="image_quality",
        check_name="Photo quality",
        status=status,  # type: ignore[arg-type]
        message=message,
        fix_suggestion=fix,
        details=_quality_details(metrics, problems),
    )


def document_type(document: DocumentInput) -> Result | None:
    """Pass when any configured keyword is found, including a close spelling."""
    keywords = _keywords(document.config.get("keywords"))
    if not keywords:
        return None
    text = document.ocr_text_masked.casefold()
    found = any(fuzz.partial_ratio(keyword.casefold(), text) >= KEYWORD_MATCH for keyword in keywords)
    name = str(document.config.get("name_en") or "this document")
    if found:
        return Result(
            check_code="document_type",
            check_name="Document type",
            status="pass",
            message=f"This looks like a {name}.",
            fix_suggestion="",
            details={"keyword_found": True},
        )
    if _readable(document):
        return Result(
            check_code="document_type",
            check_name="Document type",
            status="fail",
            message=f"This does not look like a {name}.",
            fix_suggestion=f"Upload the {name} in this slot.",
            details={"keyword_found": False, "readable": True},
        )
    return Result(
        check_code="document_type",
        check_name="Document type",
        status="warning",
        message="We could not read enough text to confirm the document type.",
        fix_suggestion="Upload a clearer photo of the whole page.",
        details={"keyword_found": False, "readable": False},
    )


def required_fields(document: DocumentInput) -> list[Result]:
    """Warn for each requested field that the heuristics cannot see."""
    fields = document.config.get("required_fields")
    if not isinstance(fields, list) or not fields:
        return []
    results: list[Result] = []
    for field_name in fields:
        code = str(field_name).strip().lower()
        if code not in {"name", "number", "date"}:
            continue
        present = _field_present(document, code)
        if present:
            results.append(
                Result(
                    check_code=f"required_field_{code}",
                    check_name="Required detail",
                    status="pass",
                    message=_field_pass(code),
                    fix_suggestion="",
                    details={"field": code, "present": True},
                )
            )
            continue
        message, fix = _field_missing(code)
        results.append(
            Result(
                check_code=f"required_field_{code}",
                check_name="Required detail",
                status="warning",
                message=message,
                fix_suggestion=fix,
                details={"field": code, "present": False},
            )
        )
    return results


def id_number_format(document: DocumentInput) -> Result | None:
    """Check the ID checksum when the rules ask for an ID number pattern."""
    rules = _rules(document.config)
    pattern = rules.get("id_number_pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        return None
    checks = document.quality_metrics.get("id_checks")
    if isinstance(checks, list):
        safe = [_safe_check(item) for item in checks]
        safe = [item for item in safe if item is not None]
        if not safe:
            return _id_result("warning", "We could not find an ID number.", "Make sure the full ID number is visible.", {"detected": False})
        if any(item["checksum_valid"] is False for item in safe):
            return _id_result(
                "warning",
                "The ID number may be misread or invalid – make sure it is fully visible.",
                "Retake the photo so every digit of the ID number is clear.",
                {"detected": True, "checks": safe},
            )
        return _id_result("pass", "The ID number looks valid.", "", {"detected": True, "checks": safe})

    # Older readings stored a count but not id_checks.
    count = document.quality_metrics.get("masked_id_count")
    if isinstance(count, (int, float)) and count > 0:
        return _id_result("pass", "An ID number was found.", "", {"detected": True, "masked_id_count": int(count)})
    return _id_result("warning", "We could not find an ID number.", "Make sure the full ID number is visible.", {"detected": False})


def date_validity(document: DocumentInput, today: date) -> Result | None:
    """Use a trusted AI date when one exists. Otherwise use the newest OCR date."""
    fields = trusted_fields(document)
    if fields is not None:
        return _ai_date_validity(document, fields, today)
    limit = _age_limit(document.config)
    if limit is None:
        return None
    dates = extract_dates(document.ocr_text_masked)
    if not dates:
        return Result(
            check_code="date_validity",
            check_name="Document date",
            status="warning",
            message="We could not find a date.",
            fix_suggestion="Make sure the issue date is visible, then read the document again.",
            details={"date_found": False},
        )
    return _age_result(max(dates), today, limit)


def _ai_date_validity(document: DocumentInput, fields: dict[str, object], today: date) -> Result | None:
    """Judge dates from AI fields. A trusted reading does not fall back to OCR."""
    issue = iso_date(fields.get("issue_date"))
    expiry = iso_date(fields.get("expiry_date"))
    limit = _age_limit(document.config)
    if expiry is not None and expiry < today:
        return Result(
            check_code="date_validity",
            check_name="Document date",
            status="fail",
            message="This document is past its expiry date.",
            fix_suggestion="Upload a document that has not expired.",
            details={"date_found": True, "expired": True},
        )
    if issue is not None and limit is not None:
        return _age_result(issue, today, limit)
    if limit is not None and issue is None:
        return Result(
            check_code="date_validity",
            check_name="Document date",
            status="warning",
            message="We could not find the issue date.",
            fix_suggestion="Make sure the issue date is visible, then read the document again.",
            details={"date_found": False},
        )
    return None


def _age_result(found: date, today: date, limit: int) -> Result:
    if found > today:
        return Result(
            check_code="date_validity",
            check_name="Document date",
            status="warning",
            message="The date on this document is in the future.",
            fix_suggestion="Check that the date is fully visible and upload the page again.",
            details={"future": True, "age_days": (found - today).days},
        )
    age = (today - found).days
    if age > limit:
        return Result(
            check_code="date_validity",
            check_name="Document date",
            status="fail",
            message="This document is too old.",
            fix_suggestion="Upload a more recent document.",
            details={"date_found": True, "age_days": age, "limit_days": limit},
        )
    return Result(
        check_code="date_validity",
        check_name="Document date",
        status="pass",
        message="The date is recent enough.",
        fix_suggestion="",
        details={"date_found": True, "age_days": age, "limit_days": limit},
    )


def _field_present(document: DocumentInput, code: str) -> bool:
    if code == "name":
        named = ai_name_present(document)
        if named is True:
            return True
        return extract_name_candidate(document.ocr_text_masked) is not None
    if code == "date":
        dated = ai_date_present(document)
        if dated is True:
            return True
        return bool(extract_dates(document.ocr_text_masked))
    checks = document.quality_metrics.get("id_checks")
    if isinstance(checks, list) and checks:
        return True
    count = document.quality_metrics.get("masked_id_count")
    if isinstance(count, (int, float)) and count > 0:
        return True
    return _NUMBER.search(document.ocr_text_masked) is not None


def _field_pass(code: str) -> str:
    if code == "date":
        return "A date is visible."
    if code == "name":
        return "A name is visible."
    return "A number is visible."


def _field_missing(code: str) -> tuple[str, str]:
    if code == "date":
        return ("We could not find a date.", "Make sure the date is visible and not cut off.")
    if code == "name":
        return ("We could not find a name.", "Make sure the name line is visible and not cut off.")
    return ("We could not find a number.", "Make sure the ID or reference number is visible.")


def _id_result(status: str, message: str, fix: str, details: dict[str, object]) -> Result:
    return Result(
        check_code="id_number_format",
        check_name="ID number",
        status=status,  # type: ignore[arg-type]
        message=message,
        fix_suggestion=fix,
        details=details,
    )


def _safe_check(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None
    last4 = item.get("last4")
    valid = item.get("checksum_valid")
    if not isinstance(last4, str) or len(last4) != 4 or not last4.isdigit():
        return None
    if not isinstance(valid, bool):
        return None
    return {"last4": last4, "checksum_valid": valid}


def _age_limit(config: dict[str, object]) -> int | None:
    days = config.get("validity_days")
    rule_days = _rules(config).get("max_age_days")
    choices = [value for value in (days, rule_days) if isinstance(value, int) and not isinstance(value, bool) and value >= 0]
    if not choices:
        return None
    return min(choices)


def _readable(document: DocumentInput) -> bool:
    metrics = document.quality_metrics
    words = metrics.get("ocr_word_count")
    if not isinstance(words, (int, float)):
        words = len(document.ocr_text_masked.split())
    confidence = metrics.get("ocr_mean_confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0
    return words >= DEFAULT_MIN_WORDS and confidence >= DEFAULT_MIN_OCR_CONFIDENCE


def _keywords(value: object) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for items in value.values():
            if isinstance(items, list):
                found.extend(str(item).strip() for item in items if str(item).strip())
        return found
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _is_photo(config: dict[str, object]) -> bool:
    fields = config.get("required_fields")
    has_fields = isinstance(fields, list) and len(fields) > 0
    return not _keywords(config.get("keywords")) and not has_fields


def _rules(config: dict[str, object]) -> dict[str, object]:
    rules = config.get("rules")
    return rules if isinstance(rules, dict) else {}


def _rule_number(config: dict[str, object], key: str, default: float) -> float:
    value = _rules(config).get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default


def _number(metrics: dict[str, object], key: str) -> float | None:
    value = metrics.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _first(problems: list[tuple[str, str, str, str]], status: str) -> tuple[str, str]:
    for item_status, message, fix, _flag in problems:
        if item_status == status:
            return message, fix
    return problems[0][1], problems[0][2]


def _quality_details(metrics: dict[str, object], problems: list[tuple[str, str, str, str]]) -> dict[str, object]:
    flags = {item[3] for item in problems}
    details: dict[str, object] = {
        "blank": "blank" in flags,
        "blur_low": "blur_low" in flags,
        "resolution_low": "resolution_low" in flags,
        "brightness_off": "brightness_off" in flags,
        "tilt_high": "tilt_high" in flags,
        "confidence_low": "confidence_low" in flags,
    }
    for key in ("width", "height", "blur_score", "brightness_mean", "skew_angle_degrees", "ocr_mean_confidence"):
        number = _number(metrics, key)
        if number is not None:
            details[key] = number
    return details
