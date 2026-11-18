"""Drop a saved readiness report when the citizen's files change.

Other keys in applications.summary stay as they are. This does not score
anything and does not call the AI.
"""

from typing import Any, Callable


def without_report(summary: object) -> dict[str, Any]:
    """Return a copy of the summary without the report key."""
    if not isinstance(summary, dict):
        return {}
    return {key: value for key, value in summary.items() if key != "report"}


def with_report(summary: object, report: dict[str, Any]) -> dict[str, Any]:
    """Put report on a copy of the summary and keep every other key."""
    merged = without_report(summary)
    merged["report"] = report
    return merged


def clear_stale_report(
    application_id: str,
    *,
    reader: Callable[[str, dict[str, str]], list[dict[str, Any]]],
    writer: Callable[[str, dict[str, str], dict[str, Any]], object],
) -> None:
    """Set the application back to draft and remove the saved report."""
    if not application_id:
        return
    rows = reader(
        "applications",
        {"id": f"eq.{application_id}", "select": "id,summary", "limit": "1"},
    )
    if not rows:
        return
    writer(
        "applications",
        {"id": f"eq.{application_id}"},
        {
            "status": "draft",
            "readiness_score": None,
            "summary": without_report(rows[0].get("summary")),
        },
    )
