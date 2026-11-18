"""Show admin config validation, cloning, and stats without a database.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe scripts\\admin_demo.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.admin.clone import build_clone_payload
from app.admin.config_validation import RequiredDocumentInput, ServiceInput, parse_model
from app.admin.stats import activity, anonymise_user_id, per_service, score_summary, top_failure_reasons, totals

COMMUNITY = {
    "slug": "community-certificate",
    "name_en": "Community Certificate",
    "name_ta": "சாதிச் சான்றிதழ்",
    "description": "Revenue Administration service REV-101.",
    "is_active": True,
    "is_verified": False,
}

COMMUNITY_DOCS = [
    {
        "code": "applicant_photo",
        "name_en": "Photo",
        "is_mandatory": True,
        "accepted_formats": ["jpg", "jpeg", "png"],
        "max_size_mb": 5,
        "keywords": {"en": [], "ta": []},
        "required_fields": [],
        "rules": {"min_width": 400, "min_height": 500, "min_blur_score": 80},
        "sort_order": 10,
        "is_active": True,
    },
    {
        "code": "address_proof",
        "name_en": "Address Proof",
        "is_mandatory": True,
        "accepted_formats": ["pdf", "jpg"],
        "max_size_mb": 5,
        "keywords": {"en": ["address"], "ta": ["முகவரி"]},
        "required_fields": ["name", "date"],
        "rules": {"min_blur_score": 100, "check_name_match": True},
        "sort_order": 20,
        "is_active": True,
    },
]


def _print_errors(title: str, payload: dict[str, object], model: type) -> None:
    parsed, errors = parse_model(model, payload)
    print(title)
    if parsed is not None:
        print("  unexpectedly valid")
        return
    for item in errors:
        print(f"  {item['field']}: {item['message']}")


def main() -> None:
    income, income_errors = parse_model(
        ServiceInput,
        {"slug": "income-certificate-demo", "name_en": "Income Certificate (Demo)"},
    )
    salary, salary_errors = parse_model(
        RequiredDocumentInput,
        {
            "code": "salary_slip",
            "name_en": "Salary slip",
            "accepted_formats": ["pdf", "jpg"],
            "max_size_mb": 4,
            "keywords": {"en": ["salary", "income"], "ta": []},
            "required_fields": ["name", "date"],
            "rules": {"min_blur_score": 80, "id_number_pattern": "^[0-9]{12}$"},
        },
    )
    print("Dummy second service")
    print(f"  valid={income is not None and salary is not None} errors={income_errors + salary_errors}")
    if income is not None:
        print(f"  slug={income.slug} active={income.is_active} verified={income.is_verified}")
    if salary is not None:
        print(f"  document={salary.code} keywords={salary.keywords['en']}")

    clone_service, clone_docs = build_clone_payload(
        COMMUNITY,
        COMMUNITY_DOCS,
        "community-certificate-copy",
        "Community Certificate (draft copy)",
    )
    print("Clone of Community Certificate")
    print(f"  slug={clone_service['slug']} active={clone_service['is_active']} verified={clone_service['is_verified']}")
    print(f"  description={clone_service['description']}")
    print(f"  documents={len(clone_docs)}")

    print("Deliberately invalid configuration")
    _print_errors("  bad slug", {"slug": "Income_Cert", "name_en": "Income"}, ServiceInput)
    _print_errors(
        "  bad regex",
        {
            "code": "id_card",
            "name_en": "ID card",
            "accepted_formats": ["jpg"],
            "max_size_mb": 2,
            "keywords": {"en": ["id"]},
            "rules": {"id_number_pattern": "(a+)+"},
        },
        RequiredDocumentInput,
    )
    _print_errors(
        "  brightness min > max",
        {
            "code": "photo",
            "name_en": "Photo",
            "accepted_formats": ["jpg"],
            "max_size_mb": 2,
            "rules": {"min_brightness": 200, "max_brightness": 10},
        },
        RequiredDocumentInput,
    )
    _print_errors(
        "  unknown rule key",
        {
            "code": "photo",
            "name_en": "Photo",
            "accepted_formats": ["jpg"],
            "max_size_mb": 2,
            "rules": {"fields_are_draft": True},
        },
        RequiredDocumentInput,
    )
    _print_errors(
        "  photo-type with name matching",
        {
            "code": "photo",
            "name_en": "Photo",
            "accepted_formats": ["jpg"],
            "max_size_mb": 2,
            "keywords": {"en": [], "ta": []},
            "required_fields": [],
            "rules": {"check_name_match": True},
        },
        RequiredDocumentInput,
    )

    profiles = [{"id": "user-a", "role": "admin"}, {"id": "user-b", "role": "citizen"}]
    applications = [
        {
            "id": "app-1",
            "service_id": "svc-1",
            "user_id": "user-a",
            "readiness_score": 90,
            "summary": {"report": {"label": "ready"}},
            "created_at": "2026-11-18T10:00:00+00:00",
        },
        {
            "id": "app-2",
            "service_id": "svc-1",
            "user_id": "user-b",
            "readiness_score": 60,
            "summary": {"report": {"label": "not_ready"}},
            "created_at": "2026-11-16T10:00:00+00:00",
        },
    ]
    uploads = [{"id": "u1", "application_id": "app-1", "status": "processed"}]
    print("Sample statistics")
    print(" ", totals(profiles, applications, uploads))
    print(" ", score_summary(applications))
    print(" ", top_failure_reasons([{"check_code": "image_quality", "check_name": "Photo quality", "status": "fail"}] * 3 + [{"check_code": "date_validity", "check_name": "Date", "status": "warning"}]))
    print(" ", per_service([{"id": "svc-1", "name_en": "Community Certificate", "slug": "community-certificate"}], applications))
    print(" ", activity(applications, 3, date(2026, 11, 18)))
    print(" ", anonymise_user_id("user-a"))


if __name__ == "__main__":
    main()
