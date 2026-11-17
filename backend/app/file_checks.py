"""Checks a citizen's upload before it is stored.

The rules are small on purpose: type, size, and the file's real header bytes.
"""

import re
import secrets

from fastapi import HTTPException, UploadFile

from app.config import settings

# Read this many bytes at a time so a huge file is rejected before it is all in memory.
CHUNK_BYTES = 64 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
MIME_FOR_EXTENSION = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "pdf": "application/pdf",
}


class UploadTooLarge(Exception):
    """Raised when the next chunk would pass the size limit."""


def allowed_bytes(document_max_mb: int) -> int:
    """The smaller of the checklist limit and the API limit."""
    try:
        document_limit = int(document_max_mb)
    except (TypeError, ValueError):
        document_limit = 0
    megabytes = min(document_limit, int(settings.MAX_UPLOAD_MB))
    if megabytes < 0:
        megabytes = 0
    return megabytes * 1024 * 1024


def extension_of(filename: str) -> str:
    """Return the lowercase extension, or an empty string when there is none."""
    cleaned = filename.replace("\\", "/").split("/")[-1]
    if "." not in cleaned:
        return ""
    return cleaned.rsplit(".", 1)[-1].lower()


def sanitize_filename(filename: str) -> str:
    """Keep a short safe name. Directories and odd characters are removed."""
    base = filename.replace("\\", "/").split("/")[-1].strip()
    base = base.lstrip(".")
    base = re.sub(r"[^A-Za-z0-9._-]", "", base)
    if not base or base in {".", ".."}:
        base = "file"
    if len(base) > 80:
        if "." in base:
            stem, ext = base.rsplit(".", 1)
            base = f"{stem[:70]}.{ext[:8]}"
        else:
            base = base[:80]
    if base.startswith("."):
        base = f"file{base}"
    return base


def sanitize_code(code: str) -> str:
    """Keep the checklist code safe to place in a storage path."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", code)[:40]
    return cleaned or "document"


def storage_path(user_id: str, application_id: str, code: str, filename: str) -> str:
    """Build {user}/{application}/{code}-{random}-{safe name}."""
    random_bit = secrets.token_hex(4)
    safe_name = sanitize_filename(filename)
    return f"{user_id}/{application_id}/{sanitize_code(code)}-{random_bit}-{safe_name}"


def magic_matches(content: bytes, extension: str) -> bool:
    """True when the first bytes are a real JPEG, PNG, or PDF."""
    if extension in {"jpg", "jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == "pdf":
        return content.startswith(b"%PDF-")
    return False


def read_limited_chunks(chunks: object, limit: int) -> bytes:
    """Join chunks and stop as soon as they pass the limit."""
    parts: list[bytes] = []
    total = 0
    for chunk in chunks:  # type: ignore[union-attr]
        if not isinstance(chunk, (bytes, bytearray)) or not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise UploadTooLarge()
        parts.append(bytes(chunk))
    return b"".join(parts)


def _bad(status: int, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=message)


async def read_upload(
    upload: UploadFile,
    limit: int,
    accepted_formats: list[str],
) -> tuple[str, str, bytes]:
    """Check the file in the required order and return extension, mime, and bytes."""
    filename = upload.filename or ""
    if not filename.strip():
        raise _bad(400, "Choose a file to upload.")

    first = await upload.read(CHUNK_BYTES)
    if not first:
        raise _bad(400, "This file is empty.")

    extension = extension_of(filename)
    accepted = {item.lower().lstrip(".") for item in accepted_formats}
    if extension not in ALLOWED_EXTENSIONS or extension not in accepted:
        raise _bad(415, "This file type is not allowed. Use JPG, PNG, or PDF.")

    declared = (upload.content_type or "").split(";", 1)[0].strip().lower()
    expected = MIME_FOR_EXTENSION[extension]
    if declared != expected:
        raise _bad(415, "The file type does not match its name.")

    if len(first) > limit:
        raise _bad(413, "This file is larger than the allowed size.")

    parts = [first]
    total = len(first)
    while True:
        chunk = await upload.read(CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise _bad(413, "This file is larger than the allowed size.")
        parts.append(chunk)

    content = b"".join(parts)
    if not magic_matches(content, extension):
        raise _bad(415, "The file contents do not match its type.")
    return extension, expected, content
