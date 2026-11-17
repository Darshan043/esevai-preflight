"""Read words from one prepared page. The text is still unmasked here."""

import pytesseract
from pytesseract import Output

from app.config import settings
from app.processing.loader import DocumentUnreadableError

if settings.TESSERACT_CMD.strip():
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD.strip()

TAMIL_WARNING = "Tamil OCR unavailable"
_installed_langs: set[str] | None = None


def run_ocr(image, langs: str | None = None) -> dict[str, str | float | int | None]:
    """Return the words, an average confidence, and which languages were used.

    A blank page returns empty text. That is not an error.
    """
    requested = (langs or settings.OCR_LANGS or "eng").strip() or "eng"
    chosen, warning = _choose_langs(requested)
    if image is None or getattr(image, "size", 0) == 0:
        return _empty(chosen, warning)

    try:
        data = pytesseract.image_to_data(
            image,
            lang=chosen,
            config="--psm 6",
            output_type=Output.DICT,
            timeout=settings.OCR_TIMEOUT_SECONDS,
        )
    except RuntimeError as exc:
        # pytesseract raises RuntimeError when the timeout fires.
        if "timeout" in str(exc).lower():
            raise DocumentUnreadableError("Reading this document took too long.") from exc
        raise DocumentUnreadableError("This document could not be read.") from exc
    except pytesseract.TesseractError as exc:
        raise DocumentUnreadableError("This document could not be read.") from exc

    words: list[str] = []
    confidences: list[float] = []
    texts = data.get("text") or []
    scores = data.get("conf") or []
    for raw_word, raw_score in zip(texts, scores):
        word = str(raw_word).strip()
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = -1.0
        if word and score >= 0:
            words.append(word)
            confidences.append(score)

    mean = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "text": " ".join(words),
        "mean_confidence": round(mean, 2),
        "word_count": len(words),
        "langs_used": chosen,
        "warning": warning,
    }


def _empty(langs: str, warning: str | None) -> dict[str, str | float | int | None]:
    return {
        "text": "",
        "mean_confidence": 0.0,
        "word_count": 0,
        "langs_used": langs,
        "warning": warning,
    }


def _choose_langs(requested: str) -> tuple[str, str | None]:
    """Drop Tamil when its trained data is missing, and say so."""
    parts = [part.strip() for part in requested.split("+") if part.strip()]
    if not parts:
        parts = ["eng"]
    installed = _languages()
    warning = None
    if "tam" in parts and "tam" not in installed:
        parts = [part for part in parts if part != "tam"]
        warning = TAMIL_WARNING
    if not parts:
        parts = ["eng"]
    return "+".join(parts), warning


def _languages() -> set[str]:
    global _installed_langs
    if _installed_langs is None:
        try:
            _installed_langs = set(pytesseract.get_languages(config=""))
        except pytesseract.TesseractError:
            _installed_langs = {"eng"}
    return _installed_langs
