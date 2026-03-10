"""Table detection and cropping for padron images.

Extracted from 13_mayo_2026/padron_provisorio/procesar_padron.py:detectar_y_recortar_tabla().
"""

from __future__ import annotations

import cv2
import numpy as np


def detect_table(img: np.ndarray) -> tuple[int, int, int, int]:
    """Detect the bounding box of the table content area.

    Uses Otsu binarization + findNonZero to locate the content region.

    Args:
        img: OpenCV image (BGR or grayscale).

    Returns:
        Bounding box as (x, y, w, h). Returns full image dimensions
        if no content is detected.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = cv2.findNonZero(binary)
    if coords is None:
        h, w = img.shape[:2]
        return 0, 0, w, h

    return cv2.boundingRect(coords)


def crop_table(img: np.ndarray, margin: int = 20) -> np.ndarray:
    """Detect and crop the table region with a margin.

    Args:
        img: OpenCV image (BGR or grayscale).
        margin: Pixel margin around the detected content.

    Returns:
        Cropped image containing the table region.
    """
    x, y, w, h = detect_table(img)

    # Apply margin with bounds checking
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(img.shape[1] - x, w + 2 * margin)
    h = min(img.shape[0] - y, h + 2 * margin)

    return img[y : y + h, x : x + w]
