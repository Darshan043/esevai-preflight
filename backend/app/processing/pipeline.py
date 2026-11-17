"""Run the whole read: load, measure, clean, OCR, then mask.

The unmasked text stays inside this function. Callers only receive the mask.
"""

import logging
import time

from app.config import settings
from app.processing.loader import DocumentUnreadableError, load_document
from app.processing.masking import check_id_numbers, mask_sensitive
from app.processing.ocr import run_ocr
from app.processing.preprocess import prepare_for_ocr
from app.processing.quality import measure_quality

logger = logging.getLogger(__name__)

PAGE_BREAK = "\n\n----- page break -----\n\n"
TEXT_LIMIT = 20000


def process_document(content_bytes: bytes, mime_type: str) -> dict[str, object]:
    """Read one file and return quality numbers plus masked text."""
    started = time.perf_counter()
    warnings: list[str] = []
    loaded = load_document(content_bytes, mime_type)
    if not loaded.images:
        raise DocumentUnreadableError("This file has no pages to read.")

    first = measure_quality(loaded.images[0])
    page_texts: list[str] = []
    confidences: list[float] = []
    word_count = 0
    langs_used = settings.OCR_LANGS

    for index, image in enumerate(loaded.images):
        metrics = first if index == 0 else measure_quality(image)
        prepared = prepare_for_ocr(image, float(metrics["skew_angle_degrees"]))
        page = run_ocr(prepared, settings.OCR_LANGS)
        warning = page.get("warning")
        if isinstance(warning, str) and warning not in warnings:
            warnings.append(warning)
        page_texts.append(str(page.get("text") or ""))
        confidences.append(float(page.get("mean_confidence") or 0))
        word_count += int(page.get("word_count") or 0)
        langs_used = str(page.get("langs_used") or langs_used)

    combined = PAGE_BREAK.join(page_texts).strip()
    # Check digits before masking. Only the last 4 digits are kept.
    id_checks = check_id_numbers(combined)
    masked, masked_count = mask_sensitive(combined)
    if len(masked) > TEXT_LIMIT:
        masked = masked[:TEXT_LIMIT]
        warnings.append("The saved text was shortened.")
    if loaded.page_count > len(loaded.images):
        warnings.append(f"Only the first {len(loaded.images)} pages were read.")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    file_type = "pdf" if "pdf" in (mime_type or "").lower() else "image"
    mean_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    # Counts and timing only. The words themselves are not logged.
    logger.info(
        "pipeline finished pages=%s words=%s masked=%s ms=%s warnings=%s",
        loaded.page_count,
        word_count,
        masked_count,
        elapsed_ms,
        len(warnings),
    )

    quality = {
        **first,
        "page_count": loaded.page_count,
        "dpi_used": settings.OCR_PDF_DPI if file_type == "pdf" else None,
        "file_type": file_type,
        "ocr_mean_confidence": mean_confidence,
        "ocr_word_count": word_count,
        "ocr_langs": langs_used,
        "masked_id_count": masked_count,
        "id_checks": id_checks,
        "processing_ms": elapsed_ms,
        "warnings": warnings,
    }
    return {"quality_metrics": quality, "ocr_text_masked": masked}
