"""Hide ID numbers before any text is saved, logged, or sent back.

Tamil digits are converted to ASCII only while we look for a number.
The stored text keeps the surrounding words and shows only the last 4 digits.
"""

import re

# Real Aadhaar numbers do not start with 0 or 1. The practice files in this
# project use 1234 5678 9012, so a leading 1 is masked too. A leading 0 is not,
# which keeps zero-padded codes out of the mask.
_GROUP = r"[1-9]\d{3}(?:[ \-]?\d{4}){2}"
_VID = re.compile(rf"(?<!\d)({_GROUP}[ \-]?\d{{4}})(?!\d)")
_AADHAAR = re.compile(rf"(?<!\d)({_GROUP})(?!\d)")
_MASKED_VID = re.compile(r"XXXX XXXX XXXX (\d{4})")
# The extra XXXX in a 16-digit mask must not also count as a 12-digit mask.
_MASKED_AADHAAR = re.compile(r"(?<!XXXX )XXXX XXXX (\d{4})")

_TAMIL_TO_ASCII = str.maketrans("௦௧௨௩௪௫௬௭௮௯", "0123456789")


def mask_sensitive(text: str) -> tuple[str, int]:
    """Replace 12-digit and 16-digit ID numbers. Returns the text and how many."""
    if not text:
        return "", 0
    folded = text.translate(_TAMIL_TO_ASCII)
    spans = _id_spans(folded)
    if not spans:
        return text, 0

    pieces: list[str] = []
    cursor = 0
    for start, end, last4, width in spans:
        pieces.append(text[cursor:start])
        pieces.append(_mask(last4, width))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), len(spans)


def extract_masked_id_suffixes(text: str) -> list[str]:
    """Return only the last 4 digits of each ID. Never the full number."""
    if not text:
        return []
    folded = text.translate(_TAMIL_TO_ASCII)
    suffixes = [last4 for _start, _end, last4, _width in _id_spans(folded)]
    if suffixes:
        return suffixes

    found: list[str] = []
    occupied: list[tuple[int, int]] = []
    for pattern in (_MASKED_VID, _MASKED_AADHAAR):
        for match in pattern.finditer(text):
            span = match.span()
            if any(not (span[1] <= start or span[0] >= end) for start, end in occupied):
                continue
            occupied.append(span)
            found.append(match.group(1))
    return found


def _id_spans(folded: str) -> list[tuple[int, int, str, int]]:
    """Find non-overlapping IDs. 16-digit numbers are taken before 12-digit ones."""
    spans: list[tuple[int, int, str, int]] = []
    for match in _VID.finditer(folded):
        digits = _digits(match.group(1))
        if len(digits) == 16:
            spans.append((match.start(1), match.end(1), digits[-4:], 16))
    for match in _AADHAAR.finditer(folded):
        start, end = match.start(1), match.end(1)
        if any(not (end <= kept[0] or start >= kept[1]) for kept in spans):
            continue
        digits = _digits(match.group(1))
        if len(digits) == 12:
            spans.append((start, end, digits[-4:], 12))
    spans.sort()
    return spans


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _mask(last4: str, width: int) -> str:
    if width == 16:
        return f"XXXX XXXX XXXX {last4}"
    return f"XXXX XXXX {last4}"
