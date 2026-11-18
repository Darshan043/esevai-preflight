"""Show sample readiness scores without a database or image files.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe scripts\\report_demo.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.report.builder import build_report
from app.report.scoring import (
    ALMOST_READY_MIN_SCORE,
    CROSS_FAIL_PENALTY,
    CROSS_WARNING_PENALTY,
    FAIL_PENALTY,
    MANDATORY_WEIGHT,
    OPTIONAL_WEIGHT,
    READY_MIN_SCORE,
    WARNING_PENALTY,
)

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def _required(code: str, name: str, *, mandatory: bool = True, sort_order: int = 1) -> dict[str, object]:
    return {
        "id": f"req-{code}",
        "code": code,
        "name_en": name,
        "name_ta": None,
        "is_mandatory": mandatory,
        "is_active": True,
        "sort_order": sort_order,
    }


def _upload(code: str) -> dict[str, object]:
    return {
        "id": f"upload-{code}",
        "required_document_id": f"req-{code}",
        "status": "processed",
        "updated_at": "2026-11-18T10:00:00+00:00",
        "created_at": "2026-11-18T10:00:00+00:00",
    }


def _result(status: str, message: str, fix: str, *, upload: str | None, check_code: str) -> dict[str, object]:
    return {
        "check_code": check_code,
        "status": status,
        "message": message,
        "fix_suggestion": fix,
        "uploaded_document_id": f"upload-{upload}" if upload else None,
    }


def _print(title: str, report: dict[str, object]) -> None:
    print(title)
    print(f"  score={report['score']}  label={report['label']}")
    print(f"  counts={report['counts']}")
    print("  next steps:")
    for step in report["next_steps"][:4]:
        print(f"    {step['priority']}. [{step['type']}] {step['text']}")
    print()


def main() -> None:
    print("Formula constants")
    print(f"  FAIL_PENALTY={FAIL_PENALTY}  WARNING_PENALTY={WARNING_PENALTY}")
    print(f"  CROSS_FAIL_PENALTY={CROSS_FAIL_PENALTY}  CROSS_WARNING_PENALTY={CROSS_WARNING_PENALTY}")
    print(f"  MANDATORY_WEIGHT={MANDATORY_WEIGHT}  OPTIONAL_WEIGHT={OPTIONAL_WEIGHT}")
    print(f"  READY_MIN_SCORE={READY_MIN_SCORE}  ALMOST_READY_MIN_SCORE={ALMOST_READY_MIN_SCORE}")
    print()

    good_required = [
        _required("photo", "Passport photo", sort_order=1),
        _required("id_card", "ID card", sort_order=2),
        _required("address", "Address proof", sort_order=3),
    ]
    good_uploads = [_upload("photo"), _upload("id_card"), _upload("address")]
    good_results = [
        _result("pass", "The photo is clear.", "", upload="photo", check_code="image_quality"),
        _result("pass", "The ID card was read.", "", upload="id_card", check_code="document_type"),
        _result("pass", "The address proof was read.", "", upload="address", check_code="document_type"),
    ]
    good = build_report({}, {}, good_required, good_uploads, good_results, NOW)
    _print("GOOD (all pass)", good)

    mixed_required = list(good_required)
    mixed_uploads = list(good_uploads)
    mixed_results = [
        _result("warning", "The photo is a little dark.", "Retake the photo in better light.", upload="photo", check_code="image_quality"),
        _result("warning", "The photo is slightly tilted.", "Hold the camera straight.", upload="photo", check_code="image_tilt"),
        _result("warning", "The date is hard to read.", "Upload a clearer copy.", upload="id_card", check_code="date_validity"),
        _result("warning", "Some ID digits are faded.", "Use a sharper scan.", upload="id_card", check_code="id_number_format"),
        _result("warning", "The address looks faint.", "Upload a clearer address proof.", upload="address", check_code="image_quality"),
    ]
    mixed = build_report({}, {}, mixed_required, mixed_uploads, mixed_results, NOW)
    _print("MIXED (warnings only)", mixed)

    bad_required = [
        _required("photo", "Passport photo", sort_order=1),
        _required("id_card", "ID card", sort_order=2),
        _required("address", "Address proof", sort_order=3),
    ]
    bad_uploads = [_upload("photo"), _upload("address")]
    bad_results = [
        _result("fail", "The photo is blurry.", "Upload a sharper photo.", upload="photo", check_code="image_quality"),
        _result("fail", "ID card is missing.", "Upload the ID card.", upload=None, check_code="missing_document"),
        _result("warning", "The address looks old.", "Upload a newer address proof.", upload="address", check_code="date_validity"),
    ]
    bad = build_report({}, {}, bad_required, bad_uploads, bad_results, NOW)
    _print("BAD (fails + missing mandatory)", bad)

    optional_required = [
        _required("photo", "Passport photo", sort_order=1),
        _required("note", "Optional note", mandatory=False, sort_order=2),
    ]
    optional_uploads = [_upload("photo")]
    optional_results = [
        _result("pass", "The photo is clear.", "", upload="photo", check_code="image_quality"),
    ]
    optional = build_report({}, {}, optional_required, optional_uploads, optional_results, NOW)
    _print("EMPTY-OPTIONAL (optional slot unused)", optional)

    print("Expected labels: GOOD=ready, MIXED=almost_ready, BAD=not_ready, EMPTY-OPTIONAL=ready")
    print(f"Actual labels: GOOD={good['label']}, MIXED={mixed['label']}, BAD={bad['label']}, EMPTY-OPTIONAL={optional['label']}")


if __name__ == "__main__":
    main()
