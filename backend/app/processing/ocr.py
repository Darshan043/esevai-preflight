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
        # PSM 3 lets Tesseract find blocks and table cells. PSM 6 assumes one
        # uniform paragraph and can skip every cell except the title.
        data = pytesseract.image_to_data(
            image,
            lang=chosen,
            config="--psm 3",
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

    text, confidences = _lines_from_data(data)
    mean = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "text": text,
        "mean_confidence": round(mean, 2),
        "word_count": len(confidences),
        "langs_used": chosen,
        "warning": warning,
    }


def _lines_from_data(data: dict) -> tuple[str, list[float]]:
    """Keep each visual line. A label and its value often sit side by side."""
    texts = data.get("text") or []
    scores = data.get("conf") or []
    blocks = data.get("block_num") or []
    paragraphs = data.get("par_num") or []
    line_numbers = data.get("line_num") or []
    lefts = data.get("left") or []
    tops = data.get("top") or []
    heights = data.get("height") or []
    grouped: dict[tuple[int, int, int], list[tuple[int, int, int, str, float]]] = {}
    for index, raw_word in enumerate(texts):
        word = str(raw_word).strip()
        try:
            score = float(scores[index])
        except (TypeError, ValueError, IndexError):
            score = -1.0
        if not word or score < 0:
            continue
        key = (
            _at(blocks, index),
            _at(paragraphs, index),
            _at(line_numbers, index),
        )
        grouped.setdefault(key, []).append(
            (_at(tops, index), _at(lefts, index), _at(heights, index, 20), word, score)
        )

    lines: list[tuple[int, int, str, list[float]]] = []
    for items in grouped.values():
        items.sort(key=lambda item: item[1])
        lines.append(
            (
                min(item[0] for item in items),
                min(item[1] for item in items),
                " ".join(item[3] for item in items),
                [item[4] for item in items],
            )
        )
    lines.sort(key=lambda item: (item[0], item[1]))
    band = _row_band(grouped)
    merged: list[tuple[int, int, str, list[float]]] = []
    for top, left, line, line_scores in lines:
        if merged and abs(top - merged[-1][0]) <= band:
            previous = merged[-1]
            if left >= previous[1]:
                merged[-1] = (previous[0], previous[1], f"{previous[2]} {line}", previous[3] + line_scores)
            else:
                merged[-1] = (min(previous[0], top), left, f"{line} {previous[2]}", line_scores + previous[3])
            continue
        merged.append((top, left, line, line_scores))
    confidences = [score for _top, _left, _line, line_scores in merged for score in line_scores]
    return "\n".join(line for _top, _left, line, _scores in merged), confidences


def _at(values: list, index: int, default: int = 0) -> int:
    try:
        return int(values[index])
    except (TypeError, ValueError, IndexError):
        return default


def _row_band(grouped: dict) -> int:
    """How close two line tops must be to count as the same table row."""
    heights = [item[2] for items in grouped.values() for item in items]
    if not heights:
        return 20
    heights.sort()
    return max(12, heights[len(heights) // 2] // 2)


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
