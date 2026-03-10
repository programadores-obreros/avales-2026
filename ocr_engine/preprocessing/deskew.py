"""Image deskew using OpenCV minAreaRect.

Extracted from 13_mayo_2026/padron_provisorio/procesar_padron.py:enderezar().
"""

from __future__ import annotations

import cv2
import numpy as np


def deskew_image(
    img: np.ndarray,
    max_angle: float = 10.0,
    min_angle: float = 0.2,
    min_coords: int = 500,
) -> tuple[np.ndarray, float]:
    """Detect and correct skew in an image.

    Uses Otsu binarization + minAreaRect to detect the dominant angle,
    then rotates to correct. Only corrects angles between min_angle
    and max_angle degrees.

    Args:
        img: OpenCV image (BGR or grayscale).
        max_angle: Maximum angle to correct (degrees). Beyond this,
            the image is returned unchanged.
        min_angle: Minimum angle to correct (degrees). Below this,
            correction is skipped (negligible skew).
        min_coords: Minimum non-zero pixel count to attempt detection.

    Returns:
        Tuple of (corrected_image, detected_angle_degrees).
        If no correction was applied, angle is 0.0.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(binary > 0))
    if len(coords) < min_coords:
        return img, 0.0

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) > max_angle or abs(angle) < min_angle:
        return img, 0.0

    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        img, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    return rotated, angle
