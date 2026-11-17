"""Show sample check results without a database or image files.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe scripts\\validate_demo.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.validation.engine import validate_application
from app.validation.models import DocumentInput, Result

TODAY = date(2026, 11, 17)


def _metrics(**extra: object) -> dict[str, object]:
    values: dict[str, object] = {
        "width": 1200,
        "height": 1600,
        "blur_score": 480,
        "brightness_mean": 140,
        "skew_angle_degrees": 0.4,
        "is_probably_blank": False,
        "ocr_mean_confidence": 92,
        "ocr_word_count": 30,
    }
    values.update(extra)
    return values


def _doc(
    code: str,
    name: str,
    text: str,
    *,
    mandatory: bool = True,
    keywords: dict[str, list[str]] | None = None,
    fields: list[str] | None = None,
    rules: dict[str, object] | None = None,
    validity_days: int | None = 365,
    metrics: dict[str, object] | None = None,
    status: str = "processed",
    sort_order: int = 1,
    present: bool = True,
) -> tuple[dict[str, object], DocumentInput | None]:
    config: dict[str, object] = {
        "id": f"req-{code}",
        "code": code,
        "name_en": name,
        "is_mandatory": mandatory,
        "is_active": True,
        "keywords": keywords if keywords is not None else {"en": [name.lower()], "ta": []},
        "required_fields": fields or [],
        "rules": rules or {},
        "validity_days": validity_days,
        "sort_order": sort_order,
    }
    if not present:
        return config, None
    document = DocumentInput(
        document_id=f"upload-{code}",
        config=config,
        quality_metrics=metrics or _metrics(),
        ocr_text_masked=text,
        status=status,
    )
    return config, document


def _print(title: str, results: list[Result]) -> None:
    print(title)
    print(f"{'Status':<10} {'Check':<24} Message")
    for result in results:
        print(f"{result.status:<10} {result.check_code:<24} {result.message}")
    if not results:
        print("(no results)")
    print()


def main() -> None:
    good_specs = [
        _doc(
            "photo",
            "Photo",
            "",
            keywords={"en": [], "ta": []},
            fields=[],
            validity_days=None,
            rules={"min_blur_score": 80, "check_name_match": False},
            sort_order=1,
        ),
        _doc(
            "address_proof",
            "Address Proof",
            "Address proof\nName: Anitha Kumar\nIssued 01/11/2026",
            keywords={"en": ["address proof"], "ta": []},
            fields=["name", "date"],
            rules={"check_name_match": True, "min_blur_score": 100},
            sort_order=2,
        ),
        _doc(
            "self_declaration",
            "Self-Declaration of Applicant",
            "Self declaration\nName: Mrs Anitha Kumar\nSigned 02/11/2026",
            keywords={"en": ["self declaration"], "ta": []},
            fields=["name", "date"],
            rules={"check_name_match": True, "min_blur_score": 100},
            sort_order=3,
        ),
    ]
    good_required = [item[0] for item in good_specs]
    good_uploads = [item[1] for item in good_specs if item[1] is not None]
    good = validate_application(good_required, good_uploads, today=TODAY)
    _print("Good set", good)

    wrong_config, wrong_doc = _doc(
        "address_proof",
        "Address Proof",
        "A shopping list for rice dal and vegetables from the market this morning",
        keywords={"en": ["address proof"]},
        fields=[],
        validity_days=None,
    )
    wrong = validate_application([wrong_config], [wrong_doc] if wrong_doc else [], today=TODAY)

    old_config, old_doc = _doc(
        "address_proof",
        "Address Proof",
        "Address proof issued 01/01/2020",
        keywords={"en": ["address proof"]},
        validity_days=90,
        fields=[],
    )
    old = validate_application([old_config], [old_doc] if old_doc else [], today=TODAY)

    left_config, left_doc = _doc(
        "address_proof",
        "Address Proof",
        "Address proof\nName: Anitha Kumar",
        keywords={"en": ["address proof"]},
        fields=[],
        validity_days=None,
        rules={"check_name_match": True},
        sort_order=1,
    )
    right_config, right_doc = _doc(
        "self_declaration",
        "Self-Declaration of Applicant",
        "Self declaration\nName: Ravi Sharma",
        keywords={"en": ["self declaration"]},
        fields=[],
        validity_days=None,
        rules={"check_name_match": True},
        sort_order=2,
    )
    names = validate_application(
        [left_config, right_config],
        [item for item in (left_doc, right_doc) if item is not None],
        today=TODAY,
    )

    photo_config, _photo = _doc("photo", "Photo", "", present=False, keywords={"en": [], "ta": []}, fields=[], validity_days=None)
    missing = validate_application([photo_config], [], today=TODAY)

    blur_config, blur_doc = _doc(
        "photo",
        "Photo",
        "",
        keywords={"en": [], "ta": []},
        fields=[],
        validity_days=None,
        metrics=_metrics(blur_score=5),
        rules={"min_blur_score": 100},
    )
    blurry = validate_application([blur_config], [blur_doc] if blur_doc else [], today=TODAY)

    _print("Wrong document", wrong)
    _print("Expired date", old)
    _print("Name mismatch", names)
    _print("Missing mandatory", missing)
    _print("Blurry photo", blurry)

    def has(results: list[Result], code: str, status: str) -> bool:
        return any(item.check_code == code and item.status == status for item in results)

    problems = []
    if any(item.status == "fail" for item in good):
        problems.append("good set has a failure")
    if not has(wrong, "document_type", "fail"):
        problems.append("wrong document was not flagged")
    if not has(old, "date_validity", "fail"):
        problems.append("expired date was not flagged")
    if not has(names, "name_consistency", "fail"):
        problems.append("name mismatch was not flagged")
    if not has(missing, "missing_document", "fail"):
        problems.append("missing document was not flagged")
    if not has(blurry, "image_quality", "fail"):
        problems.append("blurry photo was not flagged")
    if problems:
        print("DEMO FAILED")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("DEMO PASSED")


if __name__ == "__main__":
    main()
