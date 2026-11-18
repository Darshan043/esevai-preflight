"""Shapes shared by every check.

A Result is one line the citizen can read. details may hold numbers, booleans,
document codes, and last-4 digits. It must not hold names or OCR text.
"""

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["pass", "warning", "fail"]


@dataclass
class Result:
    """One check outcome."""

    check_code: str
    check_name: str
    status: Status
    message: str
    fix_suggestion: str
    details: dict[str, object] = field(default_factory=dict)
    # None means the check is about the whole application, not one file.
    uploaded_document_id: str | None = None
    sort_order: int = 0


@dataclass
class DocumentInput:
    """One uploaded file plus the checklist row that describes it."""

    document_id: str
    config: dict[str, object]
    quality_metrics: dict[str, object]
    ocr_text_masked: str
    status: str
    extracted_fields: dict[str, object] = field(default_factory=dict)
