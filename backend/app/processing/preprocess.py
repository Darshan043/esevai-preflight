"""Clean a page enough for OCR. The default result stays grayscale."""

import cv2
import numpy as np

from app.config import settings


def prepare_for_ocr(image: np.ndarray, skew_angle: float) -> np.ndarray:
    """Grayscale, gently enlarge, denoise, boost contrast, and deskew when needed."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = _upscale_if_small(gray)
    # A 3x3 blur softens scanner specks without washing out the letters.
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    if abs(skew_angle) > 0.5:
        enhanced = _deskew(enhanced, skew_angle)
    return enhanced


def threshold_for_ocr(image: np.ndarray) -> np.ndarray:
    """Optional black-and-white helper. prepare_for_ocr does not call this.

    Adaptive threshold can help a flat scan and can hurt a phone photo.
    Compare OCR confidence before keeping this result. The pipeline uses
    the contrast-enhanced grayscale instead.
    """
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )


def _upscale_if_small(gray: np.ndarray) -> np.ndarray:
    height, width = gray.shape[:2]
    short_side = min(height, width)
    if short_side <= 0 or short_side >= 1000:
        return gray
    scale = min(1000.0 / short_side, 3.0)
    new_width = int(width * scale)
    new_height = int(height * scale)
    if new_width * new_height > settings.OCR_MAX_PIXELS:
        return gray
    return cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)


def _deskew(gray: np.ndarray, skew_angle: float) -> np.ndarray:
    """Rotate the page the other way so the lines sit closer to level."""
    height, width = gray.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, -float(skew_angle), 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
