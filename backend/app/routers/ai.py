"""Gemini field extraction and plain-language explanations.

These routes never decide whether a document passes. The key stays in settings.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict

from app.ai.client import AIUnavailableError, complete_json, friendly_message
from app.ai.explanations import ExplanationParseError, build_explanation_prompt, parse_explanations
from app.ai.extraction import ExtractionParseError, build_extraction_prompt, parse_extraction
from app.ai.hygiene import with_ai_advice
from app.ai.limits import reserve_call
from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.supabase_client import SupabaseRequestError, get_rows, update_rows

logger = logging.getLogger(__name__)

router = APIRouter()

_UNAVAILABLE = "AI assistance is unavailable right now. Your standard checks still work."


class ExplainRequest(BaseModel):
    """Optional language. An empty body uses the citizen's saved language."""

    model_config = ConfigDict(extra="forbid")

    language: Literal["en", "ta"] | None = None


def _off() -> None:
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI assistance is turned off.")


def _unavailable(exc: AIUnavailableError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=friendly_message(exc.category))


def _owned_document(document_id: str, user_id: str) -> dict[str, Any]:
    rows = get_rows(
        "uploaded_documents",
        {
            "id": f"eq.{document_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,application_id,user_id,required_document_id,status,ocr_text_masked,extracted_fields,updated_at",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="This file was not found.")
    return rows[0]


def _owned_application(application_id: str, user_id: str) -> dict[str, Any]:
    rows = get_rows(
        "applications",
        {
            "id": f"eq.{application_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,user_id,service_id,summary",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="This application was not found.")
    return rows[0]


def _keywords(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    words: list[str] = []
    for key in ("en", "ta"):
        group = value.get(key)
        if isinstance(group, list):
            words.extend(str(item) for item in group if str(item).strip())
    return words


def _public_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """The fields the browser may see. The bookkeeping block stays on the server."""
    return {key: value for key, value in fields.items() if key != "_meta"}


def _cached(fields: object, updated_at: object) -> dict[str, Any] | None:
    if not isinstance(fields, dict) or "extraction_confidence" not in fields:
        return None
    meta = fields.get("_meta")
    if not isinstance(meta, dict) or not meta.get("extracted_at") or not meta.get("source_updated_at"):
        return None
    # Saving the fields moves updated_at. A new reading clears extracted_fields,
    # so a stored record belongs to the current file until that happens.
    if meta.get("source_updated_at") == updated_at or meta.get("extracted_at"):
        return fields
    return None


@router.post("/documents/{document_id}/extract")
async def extract_document(
    document_id: str,
    force: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Read structured fields from masked text. Does not change pass or fail."""
    _off()
    row = _owned_document(document_id, user.user_id)
    text = row.get("ocr_text_masked")
    if row.get("status") != "processed" or not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=409, detail="Read the document first")
    cached = None if force else _cached(row.get("extracted_fields"), row.get("updated_at"))
    if cached is not None:
        return _public_fields(cached)

    reserve_call(user.user_id)
    required_rows = get_rows(
        "required_documents",
        {
            "id": f"eq.{row.get('required_document_id')}",
            "select": "name_en,keywords",
            "limit": "1",
        },
    )
    required = required_rows[0] if required_rows else {}
    system, prompt = build_extraction_prompt(
        str(required.get("name_en") or "Document"),
        _keywords(required.get("keywords")),
        text,
    )
    model = (settings.GEMINI_MODEL or "").strip() or "gemini-3.8-flash"
    started = time.perf_counter()
    try:
        raw, usage = await run_in_threadpool(complete_json, system, prompt)
        parsed = parse_extraction(raw)
    except AIUnavailableError as exc:
        logger.info(
            "gemini extract document=%s model=%s ms=%s status=%s",
            document_id,
            model,
            int((time.perf_counter() - started) * 1000),
            exc.category,
        )
        raise _unavailable(exc) from None
    except ExtractionParseError:
        logger.info(
            "gemini extract document=%s model=%s ms=%s status=parse",
            document_id,
            model,
            int((time.perf_counter() - started) * 1000),
        )
        raise HTTPException(status_code=502, detail=_UNAVAILABLE) from None

    stored = {
        **parsed,
        "_meta": {
            "model": model,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "source_updated_at": row.get("updated_at"),
        },
    }
    try:
        update_rows("uploaded_documents", {"id": f"eq.{document_id}"}, {"extracted_fields": stored})
    except SupabaseRequestError:
        raise HTTPException(status_code=502, detail=_UNAVAILABLE) from None
    logger.info(
        "gemini extract document=%s model=%s ms=%s prompt_tokens=%s output_tokens=%s status=ok",
        document_id,
        model,
        int((time.perf_counter() - started) * 1000),
        usage["prompt_tokens"],
        usage["output_tokens"],
    )
    return _public_fields(stored)


@router.post("/applications/{application_id}/explain")
async def explain_application(
    application_id: str,
    body: ExplainRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Rewrite warning and fail messages. Pass rows are not sent."""
    _off()
    application = _owned_application(application_id, user.user_id)
    language = body.language if body and body.language else ("ta" if user.preferred_language == "ta" else "en")
    results = get_rows(
        "validation_results",
        {
            "application_id": f"eq.{application_id}",
            "select": "id,uploaded_document_id,check_code,status,message,fix_suggestion",
            "order": "created_at.asc",
        },
    )
    names = _document_names(str(application.get("service_id") or ""), results)
    items = _explain_items(results, names)
    if not items:
        return {"items": [], "overall_tip": None}

    reserve_call(user.user_id)
    system, prompt = build_explanation_prompt(items, language)
    model = (settings.GEMINI_MODEL or "").strip() or "gemini-3.8-flash"
    started = time.perf_counter()
    try:
        raw, usage = await run_in_threadpool(complete_json, system, prompt)
        parsed = parse_explanations(raw, {str(item["id"]) for item in items})
    except AIUnavailableError as exc:
        logger.info(
            "gemini explain application=%s model=%s ms=%s status=%s",
            application_id,
            model,
            int((time.perf_counter() - started) * 1000),
            exc.category,
        )
        raise _unavailable(exc) from None
    except ExplanationParseError:
        logger.info(
            "gemini explain application=%s model=%s ms=%s status=parse",
            application_id,
            model,
            int((time.perf_counter() - started) * 1000),
        )
        raise HTTPException(status_code=502, detail=_UNAVAILABLE) from None

    advice = {
        "language": language,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "items": parsed["items"],
        "overall_tip": parsed["overall_tip"],
    }
    try:
        update_rows(
            "applications",
            {"id": f"eq.{application_id}"},
            {"summary": with_ai_advice(application.get("summary"), advice)},
        )
    except SupabaseRequestError:
        raise HTTPException(status_code=502, detail=_UNAVAILABLE) from None
    logger.info(
        "gemini explain application=%s model=%s ms=%s prompt_tokens=%s output_tokens=%s status=ok",
        application_id,
        model,
        int((time.perf_counter() - started) * 1000),
        usage["prompt_tokens"],
        usage["output_tokens"],
    )
    return advice


@router.get("/applications/{application_id}/ai-advice")
def read_advice(application_id: str, user: CurrentUser = Depends(get_current_user)) -> dict[str, Any] | None:
    """Return the saved explanation, or null when there is none."""
    application = _owned_application(application_id, user.user_id)
    summary = application.get("summary")
    if not isinstance(summary, dict):
        return None
    advice = summary.get("ai_advice")
    if not isinstance(advice, dict):
        return None
    return {
        "language": advice.get("language"),
        "generated_at": advice.get("generated_at"),
        "model": advice.get("model"),
        "items": advice.get("items") if isinstance(advice.get("items"), list) else [],
        "overall_tip": advice.get("overall_tip"),
    }


def _document_names(service_id: str, results: list[dict[str, Any]]) -> dict[str, str]:
    upload_ids = [str(row.get("uploaded_document_id")) for row in results if row.get("uploaded_document_id")]
    if not upload_ids or not service_id:
        return {}
    uploads = get_rows(
        "uploaded_documents",
        {
            "id": f"in.({','.join(upload_ids)})",
            "select": "id,required_document_id",
        },
    )
    required = get_rows(
        "required_documents",
        {"service_id": f"eq.{service_id}", "select": "id,name_en"},
    )
    by_required = {str(row.get("id")): str(row.get("name_en") or "Document") for row in required}
    return {
        str(row.get("id")): by_required.get(str(row.get("required_document_id")), "Document")
        for row in uploads
    }


def _explain_items(results: list[dict[str, Any]], names: dict[str, str]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in results:
        if row.get("status") == "pass":
            continue
        upload_id = str(row.get("uploaded_document_id") or "")
        items.append(
            {
                "id": str(row.get("id") or ""),
                "document_name": names.get(upload_id, "Application"),
                "check_code": str(row.get("check_code") or ""),
                "status": str(row.get("status") or ""),
                "message": str(row.get("message") or ""),
                "fix_suggestion": str(row.get("fix_suggestion") or ""),
            }
        )
        if len(items) >= 25:
            break
    return [item for item in items if item["id"]]
