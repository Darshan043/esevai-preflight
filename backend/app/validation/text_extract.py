"""Best-guess reading of dates and names from masked OCR text.

This is a heuristic. It does not call an AI model. Step 9 will improve
name and date reading. Callers must not put the guessed name into a message
or into result details.
"""

import re
from datetime import date

# Tamil digits become ASCII only while we look. The stored text is unchanged.
_TAMIL_TO_ASCII = str.maketrans("௦௧௨௩௪௫௬௭௮௯", "0123456789")
_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{2}|\d{4})(?!\d)")
_TITLES = ("MR", "MRS", "MS", "DR", "THIRU", "SELVI", "TMT", "THIRUMATHI")
# Longer labels first so "name of the applicant" wins over "name".
_LABELS = (
    "name of the applicant",
    "name of applicant",
    "applicant name",
    "holder",
    "name",
    "பெயர்",
)


def extract_dates(text: str) -> list[date]:
    """Find calendar dates. Two-digit years use 1970–1999 and 2000–2069."""
    if not text:
        return []
    folded = text.translate(_TAMIL_TO_ASCII)
    found: list[date] = []
    seen: set[date] = set()
    for match in _DATE.finditer(folded):
        parsed = _parse_date(match.group(1), match.group(2), match.group(3))
        if parsed is None or parsed in seen:
            continue
        seen.add(parsed)
        found.append(parsed)
    return found


def extract_name_candidate(text: str) -> str | None:
    """Return a normalised name, or None when the line is not clearly a name.

    Looks for an English or Tamil name label first. Otherwise it uses the
    first short line that is mostly letters. This is a best guess.
    """
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        labelled = _after_label(line)
        if labelled is None and _is_label(line) and index + 1 < len(lines):
            labelled = lines[index + 1]
        if labelled:
            name = _normalise_name(labelled)
            if name:
                return name
    for line in lines:
        if _is_label(line):
            continue
        if _looks_like_name_line(line):
            name = _normalise_name(line)
            if name:
                return name
    return None


def normalise_name(value: str) -> str:
    """Public wrapper so tests can compare the same way the engine does."""
    return _normalise_name(value)


def _parse_date(day_text: str, month_text: str, year_text: str) -> date | None:
    try:
        day = int(day_text)
        month = int(month_text)
        year = int(year_text)
    except ValueError:
        return None
    if year < 100:
        # 70–99 are 1970–1999. 00–69 are 2000–2069.
        year += 1900 if year >= 70 else 2000
    if not 1900 <= year <= 2100:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _is_label(line: str) -> bool:
    compact = line.strip(" :.-").casefold()
    return compact in _LABELS


def _after_label(line: str) -> str | None:
    folded = line.casefold()
    for label in _LABELS:
        start = 0
        while True:
            found = folded.find(label, start)
            if found < 0:
                break
            before_ok = found == 0 or not folded[found - 1].isalnum()
            after = found + len(label)
            if before_ok:
                rest = line[after:].strip(" :.-")
                if rest:
                    return rest
            start = after
    return None


def _looks_like_name_line(line: str) -> bool:
    words = [word for word in re.split(r"\s+", line) if word]
    if len(words) < 2 or len(words) > 5:
        return False
    letters = [char for char in line if char.isalpha()]
    if len("".join(words)) < 6 or len(letters) < len(line) * 0.7:
        return False
    return True


def _normalise_name(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\u0B80-\u0BFF ]+", " ", value).upper()
    parts = [part for part in cleaned.split() if part]
    while parts and parts[0] in _TITLES:
        parts = parts[1:]
    if any(char.isdigit() for char in "".join(parts)):
        return ""
    if len("".join(parts)) < 3:
        return ""
    return " ".join(parts)
