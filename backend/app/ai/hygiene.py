"""Drop saved AI advice when the checklist changes.

Other keys in applications.summary are left as they are.
"""

from typing import Any, Callable


def without_ai_advice(summary: object) -> dict[str, Any]:
    """Return a copy of the summary with ai_advice removed."""
    if not isinstance(summary, dict):
        return {}
    return {key: value for key, value in summary.items() if key != "ai_advice"}


def with_ai_advice(summary: object, advice: dict[str, Any]) -> dict[str, Any]:
    """Put ai_advice on a copy of the summary and keep every other key."""
    merged = without_ai_advice(summary)
    merged["ai_advice"] = advice
    return merged


def clear_ai_advice(
    application_id: str,
    *,
    reader: Callable[[str, dict[str, str]], list[dict[str, Any]]],
    writer: Callable[[str, dict[str, str], dict[str, Any]], object],
) -> None:
    """Remove ai_advice for one application. The caller handles storage errors."""
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
        {"summary": without_ai_advice(rows[0].get("summary"))},
    )
