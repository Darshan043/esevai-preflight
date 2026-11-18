"""Validate service and checklist configuration before it is saved.

The Step 8 engine reads these rows at runtime, so an invalid rule must never
be stored. These functions do not talk to the database.
"""

from __future__ import annotations

import re
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

ALLOWED_FORMATS = {"jpg", "jpeg", "png", "pdf"}
ALLOWED_FIELDS = {"name", "number", "date"}
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,59}$")
CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,49}$")
NESTED_QUANTIFIER = re.compile(r"\([^()]*[+*][^()]*\)[+*]")
QUANTIFIER_GROUP = re.compile(r"\([^()]*([+*?]|\{\d+(,\d*)?})[^()]*\)")


def validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    """Turn a Pydantic error into field/message pairs the form can show."""
    found: list[dict[str, str]] = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc") or () if part != "body")
        message = str(item.get("msg") or "This value is not valid.")
        if message.lower().startswith("value error, "):
            message = message[13:]
        elif message.lower().startswith("value error "):
            message = message[12:]
        found.append({"field": loc or "form", "message": message})
    return found


def parse_model(model: type[BaseModel], data: object) -> tuple[BaseModel | None, list[dict[str, str]]]:
    """Validate a dict. Returns (value, []) or (None, errors)."""
    try:
        return model.model_validate(data), []
    except ValidationError as exc:
        return None, validation_errors(exc)


class Rules(BaseModel):
    """Optional quality and text rules. Unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")

    min_width: int | None = Field(default=None, ge=100, le=10000)
    min_height: int | None = Field(default=None, ge=100, le=10000)
    min_blur_score: int | None = Field(default=None, ge=0, le=5000)
    min_brightness: int | None = Field(default=None, ge=0, le=255)
    max_brightness: int | None = Field(default=None, ge=0, le=255)
    id_number_pattern: str | None = Field(default=None, max_length=80)
    max_age_days: int | None = Field(default=None, ge=1, le=3650)
    check_name_match: bool | None = None

    @field_validator("id_number_pattern")
    @classmethod
    def pattern_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if NESTED_QUANTIFIER.search(text) or len(QUANTIFIER_GROUP.findall(text)) > 2:
            raise ValueError("This ID pattern is too complex and could hang the server.")
        try:
            compiled = re.compile(text)
        except re.error as exc:
            raise ValueError("This ID pattern is not a valid regular expression.") from exc
        sample = "a" * 200
        started = time.perf_counter()
        compiled.search(sample)
        if time.perf_counter() - started > 0.05:
            raise ValueError("This ID pattern takes too long to run. Use a simpler pattern.")
        return text

    @model_validator(mode="after")
    def brightness_range(self) -> Rules:
        if self.min_brightness is not None and self.max_brightness is not None:
            if self.max_brightness <= self.min_brightness:
                raise ValueError("Maximum brightness must be greater than minimum brightness.")
        return self


class ServiceInput(BaseModel):
    """Fields that can be saved on a services row."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=3, max_length=60)
    name_en: str = Field(min_length=1, max_length=120)
    name_ta: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = False
    is_verified: bool = False
    confirm_verified: bool = False

    @field_validator("slug")
    @classmethod
    def slug_format(cls, value: str) -> str:
        text = value.strip()
        if not SLUG_PATTERN.fullmatch(text):
            raise ValueError("Use 3–60 lowercase letters, digits, and hyphens, starting with a letter.")
        return text

    @field_validator("name_en", "name_ta", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @model_validator(mode="after")
    def verified_needs_confirm(self) -> ServiceInput:
        if self.is_verified and not self.confirm_verified:
            raise ValueError("Tick confirm_verified after you have checked the official e-Sevai portal.")
        return self


class RequiredDocumentInput(BaseModel):
    """Fields that can be saved on a required_documents row."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=50)
    name_en: str = Field(min_length=1, max_length=120)
    name_ta: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_mandatory: bool = True
    accepted_formats: list[str]
    max_size_mb: int = Field(ge=1, le=5)
    validity_days: int | None = Field(default=None, ge=1, le=3650)
    keywords: dict[str, list[str]] = Field(default_factory=lambda: {"en": [], "ta": []})
    required_fields: list[str] = Field(default_factory=list)
    rules: Rules = Field(default_factory=Rules)
    sort_order: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def code_format(cls, value: str) -> str:
        text = value.strip()
        if not CODE_PATTERN.fullmatch(text):
            raise ValueError("Use 2–50 lowercase letters, digits, and underscores, starting with a letter.")
        return text

    @field_validator("name_en", "name_ta", "description")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("accepted_formats")
    @classmethod
    def formats_allowed(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            text = str(item).strip().lower()
            if text not in ALLOWED_FORMATS:
                raise ValueError("Accepted formats must be jpg, jpeg, png, or pdf.")
            if text not in cleaned:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("Choose at least one accepted format.")
        return cleaned

    @field_validator("required_fields")
    @classmethod
    def fields_allowed(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip().lower()
            if text not in ALLOWED_FIELDS:
                raise ValueError('Required fields must be "name", "number", or "date".')
            if text not in cleaned:
                cleaned.append(text)
        return cleaned

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        cleaned: dict[str, list[str]] = {"en": [], "ta": []}
        for lang in ("en", "ta"):
            items = value.get(lang) if isinstance(value, dict) else None
            if items is None:
                continue
            if not isinstance(items, list):
                raise ValueError("Keywords must be lists of words.")
            if len(items) > 15:
                raise ValueError("Each language can have at most 15 keywords.")
            seen: set[str] = set()
            for raw in items:
                word = " ".join(str(raw).split())
                if any(ord(char) < 32 for char in word):
                    raise ValueError("Keywords cannot contain control characters.")
                if not word:
                    continue
                if len(word) < 2 or len(word) > 60:
                    raise ValueError("Each keyword must be 2–60 characters.")
                key = word.casefold()
                if key in seen:
                    continue
                seen.add(key)
                cleaned[lang].append(word)
        extra = set(value.keys()) - {"en", "ta"} if isinstance(value, dict) else set()
        if extra:
            raise ValueError('Keywords may only use the "en" and "ta" lists.')
        return cleaned

    @model_validator(mode="after")
    def photo_type_has_no_text_rules(self) -> RequiredDocumentInput:
        has_keywords = bool(self.keywords.get("en") or self.keywords.get("ta"))
        if has_keywords or self.required_fields:
            return self
        pattern = self.rules.id_number_pattern
        if pattern:
            raise ValueError("A photo-type document cannot use an ID number pattern.")
        if self.rules.check_name_match:
            raise ValueError("A photo-type document cannot compare names with other documents.")
        return self


def document_row(parsed: RequiredDocumentInput) -> dict[str, Any]:
    """JSON that can be written to required_documents."""
    return {
        "code": parsed.code,
        "name_en": parsed.name_en,
        "name_ta": parsed.name_ta,
        "description": parsed.description,
        "is_mandatory": parsed.is_mandatory,
        "accepted_formats": parsed.accepted_formats,
        "max_size_mb": parsed.max_size_mb,
        "validity_days": parsed.validity_days,
        "keywords": parsed.keywords,
        "required_fields": parsed.required_fields,
        "rules": parsed.rules.model_dump(exclude_none=True),
        "sort_order": parsed.sort_order,
        "is_active": parsed.is_active,
    }


def service_row(parsed: ServiceInput) -> dict[str, Any]:
    """JSON that can be written to services. confirm_verified is not stored."""
    return {
        "slug": parsed.slug,
        "name_en": parsed.name_en,
        "name_ta": parsed.name_ta,
        "description": parsed.description,
        "is_active": parsed.is_active,
        "is_verified": parsed.is_verified,
    }
