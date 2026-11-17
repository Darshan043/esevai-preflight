"""Measure a page. These numbers describe the picture. They do not pass or fail it."""

import cv2
import numpy as np


def measure_quality(image: np.ndarray) -> dict[str, float | int | bool]:
    """Return size, sharpness, brightness, contrast, tilt, and a blank-page flag."""
    if image is None or image.size == 0:
        return _empty()

    gray = _gray(image)
    height, width = gray.shape[:2]
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    edges = cv2.Canny(gray, 100, 200)
    edge_fraction = float(edges.mean()) / 255.0
    # A blank scan is almost one flat colour and has almost no ink edges.
    blank = contrast < 12.0 and edge_fraction < 0.005

    return {
        "width": int(width),
        "height": int(height),
        "megapixels": round((width * height) / 1_000_000, 3),
        "blur_score": round(blur_score, 2),
        "brightness_mean": round(brightness, 1),
        "contrast_std": round(contrast, 1),
        "skew_angle_degrees": round(_skew_angle(gray), 2),
        "is_probably_blank": bool(blank),
    }


def _empty() -> dict[str, float | int | bool]:
    return {
        "width": 0,
        "height": 0,
        "megapixels": 0.0,
        "blur_score": 0.0,
        "brightness_mean": 0.0,
        "contrast_std": 0.0,
        "skew_angle_degrees": 0.0,
        "is_probably_blank": True,
    }


def _gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _skew_angle(gray: np.ndarray) -> float:
    """Estimate how far the ink is tilted. 0 means level, or that we cannot tell."""
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ys, xs = np.where(ink > 0)
    if len(xs) < 80:
        return 0.0
    points = np.column_stack((xs, ys)).astype(np.float32)
    angle = float(cv2.minAreaRect(points)[-1])
    # OpenCV reports the angle in the range -90..0. Shift it into -45..45.
    if angle < -45.0:
        angle = 90.0 + angle
    if angle > 45.0:
        angle = angle - 90.0
    if abs(angle) < 0.2:
        return 0.0
    return max(-45.0, min(45.0, angle))
