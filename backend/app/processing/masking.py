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


# Verhoeff tables. Aadhaar uses this checksum. The last digit is the check digit.
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_checksum(number: str) -> int:
    """Walk the digits from the right. Zero means the check digit matches."""
    check = 0
    for index, char in enumerate(reversed(number)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[index % 8][int(char)]]
    return check


def verhoeff_valid(number: str) -> bool:
    """True when every character is a digit and the Verhoeff check digit matches."""
    return number.isdigit() and verhoeff_checksum(number) == 0


def verhoeff_check_digit(body: str) -> str:
    """Return the digit that makes body + digit pass the Verhoeff check."""
    return str(_VERHOEFF_INV[verhoeff_checksum(f"{body}0")])


def check_id_numbers(text: str) -> list[dict[str, object]]:
    """Find 12-digit IDs and report only the last 4 digits plus the checksum.

    Tamil digits are converted for detection, the same way masking does it.
    A 16-digit number is not reported here. The full number is never returned.
    """
    if not text:
        return []
    folded = text.translate(_TAMIL_TO_ASCII)
    found: list[dict[str, object]] = []
    for start, end, last4, width in _id_spans(folded):
        if width != 12 or len(last4) != 4:
            continue
        digits = _digits(folded[start:end])
        if len(digits) != 12:
            continue
        found.append(
            {
                "type": "aadhaar",
                "last4": last4,
                "checksum_valid": verhoeff_valid(digits),
            }
        )
    return found


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
