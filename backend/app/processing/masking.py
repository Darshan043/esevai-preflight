"""Hide ID numbers before any text is saved, logged, or sent back.

Tamil digits are converted to ASCII only while we look for a number.
The stored text keeps the surrounding words and shows only the last 4 digits.
"""

import re

# A separator inside one ID: nothing, one space, one hyphen, or a line break.
# A line break may have spaces beside it. Two IDs are not joined by this.
_SEP = r"(?:[ \t]*\r?\n[ \t]*|[ \t]|-)?"
# Real Aadhaar numbers do not start with 0 or 1. The practice files in this
# project use 1234 5678 9012, so a leading 1 is masked too. A leading 0 is not,
# which keeps zero-padded codes out of the mask.
_GROUP = rf"[1-9]\d{{3}}(?:{_SEP}\d{{4}}){{2}}"
_VID = re.compile(rf"(?<!\d)({_GROUP}{_SEP}\d{{4}})(?!\d)")
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
    """Find non-overlapping IDs. A real 16-digit number wins over a 12-digit one.

    A 12-digit number grows into a 16-digit number only when the extra four
    digits are not the start of another ID. Whitespace between two IDs must
    not glue them together.
    """
    twelves = _collect(_AADHAAR, folded, 12)
    spans: list[tuple[int, int, str, int]] = []
    for start, end, last4 in twelves:
        if _overlaps(start, end, spans):
            continue
        longer = _sixteen_at(folded, start)
        if longer is None or _opens_another_id(folded, end, longer[1], twelves):
            spans.append((start, end, last4, 12))
            continue
        spans.append((longer[0], longer[1], longer[2], 16))
    for start, end, last4 in _collect(_VID, folded, 16):
        if _overlaps(start, end, spans):
            continue
        spans.append((start, end, last4, 16))
    spans.sort()
    return _prefer_unique_splits(folded, spans)


def _collect(pattern: re.Pattern[str], folded: str, width: int) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    for match in pattern.finditer(folded):
        digits = _digits(match.group(1))
        if len(digits) == width:
            found.append((match.start(1), match.end(1), digits[-4:]))
    return found


def _sixteen_at(folded: str, start: int) -> tuple[int, int, str] | None:
    """Return the 16-digit ID that begins at start, if one does."""
    match = _VID.search(folded, start)
    if match is None or match.start(1) != start:
        return None
    digits = _digits(match.group(1))
    if len(digits) != 16:
        return None
    return match.start(1), match.end(1), digits[-4:]


def _opens_another_id(
    folded: str,
    twelve_end: int,
    sixteen_end: int,
    twelves: list[tuple[int, int, str]],
) -> bool:
    """True when the extra four digits are the first group of the next ID."""
    extra_start = _first_digit(folded, twelve_end, sixteen_end)
    if extra_start is None:
        return False
    return any(item[0] == extra_start for item in twelves)


def _overlaps(start: int, end: int, spans: list[tuple[int, int, str, int]]) -> bool:
    return any(not (end <= kept[0] or start >= kept[1]) for kept in spans)


def _first_digit(text: str, start: int, end: int) -> int | None:
    for index in range(start, end):
        if text[index].isdigit():
            return index
    return None


# A whole run of 4-digit groups. Compact numbers use an empty separator.
_RUN = re.compile(rf"(?<!\d)([1-9]\d{{3}}(?:{_SEP}\d{{4}})+)(?!\d)")


def _prefer_unique_splits(
    folded: str,
    spans: list[tuple[int, int, str, int]],
) -> list[tuple[int, int, str, int]]:
    """Use the only legal split when one run can be divided in just one way.

    Seven groups can be a 12-digit ID plus a 16-digit ID, or the reverse.
    That run is left to the earlier rule. Eight groups can only be two
    16-digit IDs, so the last group is not left visible.
    """
    corrected = list(spans)
    for match in _RUN.finditer(folded):
        body = match.group(1)
        groups = list(re.finditer(r"\d{4}", body))
        if len(body) == 4 * len(groups):
            continue
        sizes = _unique_partition(len(groups))
        if sizes is None:
            continue
        start, end = match.start(1), match.end(1)
        corrected = [item for item in corrected if item[1] <= start or item[0] >= end]
        corrected.extend(_emit_groups(folded, start, groups, sizes))
    corrected.sort()
    return corrected


def _unique_partition(count: int) -> tuple[int, ...] | None:
    """The only way to add 3s and 4s to count, or None when there is not one."""
    if count <= 0 or count > 64:
        return None
    ways = [0] * (count + 1)
    ways[0] = 1
    for index in range(1, count + 1):
        total = 0
        if index >= 3:
            total += ways[index - 3]
        if index >= 4:
            total += ways[index - 4]
        ways[index] = min(total, 2)
    if ways[count] != 1:
        return None
    parts: list[int] = []
    left = count
    while left:
        took_three = left >= 3 and ways[left - 3] == 1
        took_four = left >= 4 and ways[left - 4] == 1
        if took_three == took_four:
            return None
        size = 3 if took_three else 4
        parts.append(size)
        left -= size
    return tuple(parts)


def _emit_groups(
    folded: str,
    base: int,
    groups: list[re.Match[str]],
    sizes: tuple[int, ...],
) -> list[tuple[int, int, str, int]]:
    emitted: list[tuple[int, int, str, int]] = []
    index = 0
    for size in sizes:
        chunk = groups[index:index + size]
        span_start = base + chunk[0].start()
        span_end = base + chunk[-1].end()
        width = 16 if size == 4 else 12
        emitted.append((span_start, span_end, _digits(folded[span_start:span_end])[-4:], width))
        index += size
    return emitted


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _mask(last4: str, width: int) -> str:
    if width == 16:
        return f"XXXX XXXX XXXX {last4}"
    return f"XXXX XXXX {last4}"
