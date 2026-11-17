"""Turn an uploaded file into pictures the rest of the pipeline can measure."""

import shutil
import tempfile
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

Image.MAX_IMAGE_PIXELS = settings.OCR_MAX_PIXELS


class DocumentUnreadableError(Exception):
    """The file is empty, damaged, encrypted, or too large to read safely."""


@dataclass
class LoadedDocument:
    """Pictures in BGR order, plus how many pages the file really has."""

    images: list[np.ndarray]
    page_count: int


def load_document(content_bytes: bytes, mime_type: str) -> LoadedDocument:
    """Decode a JPEG, PNG, or PDF. PDFs keep only the first few pages."""
    if not content_bytes:
        raise DocumentUnreadableError("This file is empty.")

    kind = (mime_type or "").lower()
    if kind in {"image/jpeg", "image/jpg", "image/png"}:
        return LoadedDocument([_decode_image(content_bytes)], 1)
    if kind == "application/pdf":
        return _decode_pdf(content_bytes)
    if content_bytes.startswith(b"%PDF"):
        return _decode_pdf(content_bytes)
    if content_bytes.startswith(b"\xff\xd8") or content_bytes.startswith(b"\x89PNG"):
        return LoadedDocument([_decode_image(content_bytes)], 1)
    raise DocumentUnreadableError("This file could not be read. Use a JPG, PNG, or PDF.")


def _too_many_pixels(width: int, height: int) -> bool:
    return width < 1 or height < 1 or width * height > settings.OCR_MAX_PIXELS


def _decode_image(content_bytes: bytes) -> np.ndarray:
    """Open one photo, honour its rotation tag, and return a BGR array."""
    Image.MAX_IMAGE_PIXELS = settings.OCR_MAX_PIXELS
    try:
        with Image.open(io_bytes(content_bytes)) as opened:
            opened.load()
            upright = ImageOps.exif_transpose(opened)
            if upright is None:
                raise DocumentUnreadableError("This image could not be read.")
            rgb = upright.convert("RGB")
            if _too_many_pixels(rgb.width, rgb.height):
                raise DocumentUnreadableError("This image is too large to read.")
            array = np.asarray(rgb)
    except DocumentUnreadableError:
        raise
    except Image.DecompressionBombError as exc:
        raise DocumentUnreadableError("This image is too large to read.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DocumentUnreadableError(
            "This file could not be read. It may be damaged or password-protected."
        ) from exc
    return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)


def io_bytes(content_bytes: bytes):
    """Wrap bytes so Pillow can open them. Kept tiny so tests can reuse it."""
    import io

    return io.BytesIO(content_bytes)


def _poppler_kwargs() -> dict[str, str]:
    folder = settings.POPPLER_PATH.strip()
    if not folder:
        return {}
    return {"poppler_path": folder}


def _decode_pdf(content_bytes: bytes) -> LoadedDocument:
    """Rasterise the first OCR_MAX_PDF_PAGES pages and remember the real count."""
    from pdf2image import convert_from_bytes, pdfinfo_from_bytes
    from pdf2image.exceptions import (
        PDFInfoNotInstalledError,
        PDFPageCountError,
        PDFPopplerTimeoutError,
        PDFSyntaxError,
    )

    folder = tempfile.mkdtemp(prefix="esevai-pdf-")
    try:
        try:
            info = pdfinfo_from_bytes(content_bytes, **_poppler_kwargs())
            page_count = int(info.get("Pages") or 0)
        except PDFInfoNotInstalledError as exc:
            raise DocumentUnreadableError("The PDF reader is not available on this server.") from exc
        except (PDFPageCountError, PDFSyntaxError, PDFPopplerTimeoutError, ValueError) as exc:
            raise DocumentUnreadableError(
                "This file could not be read. It may be damaged or password-protected."
            ) from exc
        except Exception as exc:
            raise DocumentUnreadableError(
                "This file could not be read. It may be damaged or password-protected."
            ) from exc

        if page_count < 1:
            raise DocumentUnreadableError("This PDF has no pages to read.")

        last_page = min(page_count, max(1, settings.OCR_MAX_PDF_PAGES))
        try:
            pictures = convert_from_bytes(
                content_bytes,
                dpi=settings.OCR_PDF_DPI,
                first_page=1,
                last_page=last_page,
                output_folder=folder,
                **_poppler_kwargs(),
            )
        except PDFInfoNotInstalledError as exc:
            raise DocumentUnreadableError("The PDF reader is not available on this server.") from exc
        except (PDFPageCountError, PDFSyntaxError, PDFPopplerTimeoutError, ValueError, OSError) as exc:
            raise DocumentUnreadableError(
                "This file could not be read. It may be damaged or password-protected."
            ) from exc
        except Exception as exc:
            raise DocumentUnreadableError(
                "This file could not be read. It may be damaged or password-protected."
            ) from exc

        images: list[np.ndarray] = []
        for picture in pictures:
            rgb = picture.convert("RGB")
            if _too_many_pixels(rgb.width, rgb.height):
                raise DocumentUnreadableError("This image is too large to read.")
            images.append(cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR))
        if not images:
            raise DocumentUnreadableError("This PDF has no pages to read.")
        return LoadedDocument(images, page_count)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
