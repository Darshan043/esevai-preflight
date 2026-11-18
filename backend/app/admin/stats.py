"""Turn lists of rows into admin statistics. No database calls.

Statistics reflect current data; validation results are replaced whenever a
check is re-run.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

ROW_CAP = 5000


def anonymise_user_id(user_id: str) -> str:
    """A short label. The full user id is never shown."""
    digest = sha256(user_id.encode("utf-8")).hexdigest()[:6]
    return f"User #{digest}"


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        stamp = value
    elif isinstance(value, str) and value:
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.date()


def _label(application: dict[str, Any]) -> str | None:
    summary = application.get("summary")
    if not isinstance(summary, dict):
        return None
    report = summary.get("report")
    if not isinstance(report, dict):
        return None
    label = report.get("label")
    if label in {"ready", "almost_ready", "not_ready"}:
        return str(label)
    return None


def totals(
    profiles: list[dict[str, Any]],
    applications: list[dict[str, Any]],
    uploads: list[dict[str, Any]],
) -> dict[str, int]:
    admins = sum(1 for row in profiles if row.get("role") == "admin")
    citizens = sum(1 for row in profiles if row.get("role") == "citizen")
    checked = sum(1 for row in applications if row.get("readiness_score") is not None)
    processed = sum(1 for row in uploads if row.get("status") == "processed")
    return {
        "users": len(profiles),
        "admins": admins,
        "citizens": citizens,
        "applications": len(applications),
        "applications_checked": checked,
        "documents_uploaded": len(uploads),
        "documents_processed": processed,
    }


def score_summary(applications: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [int(row["readiness_score"]) for row in applications if isinstance(row.get("readiness_score"), int)]
    average = round(sum(scores) / len(scores), 1) if scores else None
    distribution = {"ready": 0, "almost_ready": 0, "not_ready": 0}
    for row in applications:
        label = _label(row)
        if label:
            distribution[label] += 1
    return {"average": average, "distribution": distribution}


def top_failure_reasons(results: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    names: dict[tuple[str, str], str] = {}
    for row in results:
        status = str(row.get("status") or "")
        if status not in {"fail", "warning"}:
            continue
        code = str(row.get("check_code") or "")
        if not code:
            continue
        key = (code, status)
        counts[key] += 1
        name = row.get("check_name")
        if isinstance(name, str) and name and key not in names:
            names[key] = name
    ranked = []
    for (code, status), count in counts.most_common(limit):
        ranked.append(
            {
                "check_code": code,
                "check_name": names.get((code, status)),
                "status": status,
                "count": count,
            }
        )
    return ranked


def per_service(
    services: list[dict[str, Any]],
    applications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in applications:
        grouped[str(row.get("service_id") or "")].append(row)
    rows = []
    for service in services:
        service_id = str(service.get("id") or "")
        owned = grouped.get(service_id, [])
        checked = [item for item in owned if isinstance(item.get("readiness_score"), int)]
        average = round(sum(int(item["readiness_score"]) for item in checked) / len(checked), 1) if checked else None
        rows.append(
            {
                "service_id": service_id,
                "name_en": service.get("name_en"),
                "slug": service.get("slug"),
                "applications": len(owned),
                "checked": len(checked),
                "average_score": average,
            }
        )
    return rows


def activity(
    applications: list[dict[str, Any]],
    days: int,
    today: date,
) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in applications:
        created = _as_date(row.get("created_at"))
        if created is None:
            continue
        counts[created.isoformat()] += 1
    series = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        series.append({"date": key, "count": counts.get(key, 0)})
    return series


def recent_checks(
    applications: list[dict[str, Any]],
    services: list[dict[str, Any]],
    uploads: list[dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    names = {str(row.get("id") or ""): str(row.get("name_en") or "Service") for row in services}
    upload_counts: Counter[str] = Counter()
    for row in uploads:
        upload_counts[str(row.get("application_id") or "")] += 1
    ordered = sorted(applications, key=lambda row: str(row.get("created_at") or ""), reverse=True)
    found = []
    for row in ordered[:limit]:
        app_id = str(row.get("id") or "")
        found.append(
            {
                "id": app_id,
                "service_name": names.get(str(row.get("service_id") or ""), "Service"),
                "label": _label(row),
                "score": row.get("readiness_score"),
                "created_at": row.get("created_at"),
                "checked_at": row.get("updated_at") if row.get("readiness_score") is not None else None,
                "document_count": upload_counts.get(app_id, 0),
                "user_label": anonymise_user_id(str(row.get("user_id") or "")),
            }
        )
    return found
