"""Orientation detection — tries rotations to find the correct one.

Extracted from 13_mayo_2026/padron_provisorio/procesar_tanda.py.
"""

from __future__ import annotations

import re

import cv2
import numpy as np

from .engine import OcrEngine

# Pattern to detect "Pagina XX" or "Pag. XX" in OCR text
PAGE_PATTERN = re.compile(r"[Pp][áa]gina\s*[:\s]*(\d+)", re.IGNORECASE)
PAGE_PATTERN_SHORT = re.compile(r"[Pp]ag\.?\s*(\d+)", re.IGNORECASE)


class OrientationDetector:
    """Detect correct image orientation by trying 4 rotations.

    For each rotation (0, 90, 180, 270), runs OCR and looks for
    "Pagina XX" pattern to determine which orientation is correct.
    """

    def __init__(self, engine: OcrEngine) -> None:
        self._engine = engine

    def detect(self, image: np.ndarray) -> tuple[int, int]:
        """Detect correct rotation and page number.

        Args:
            image: OpenCV image (BGR or grayscale).

        Returns:
            Tuple of (rotation_degrees, page_number).
            rotation_degrees is 0, 90, 180, or 270.
            page_number is 0 if not detected.
        """
        best_rotation = 0
        best_page = 0
        best_score = 0

        for degrees in (0, 90, 180, 270):
            rotated = self._rotate(image, degrees)
            result = self._engine.recognize(rotated)
            page_num = self._extract_page_number(result.raw_text)
            score = self._score_text(result.raw_text)

            if page_num > 0 and score > best_score:
                best_rotation = degrees
                best_page = page_num
                best_score = score

        return best_rotation, best_page

    @staticmethod
    def _rotate(image: np.ndarray, degrees: int) -> np.ndarray:
        """Rotate image by 0, 90, 180, or 270 degrees."""
        if degrees == 0:
            return image
        if degrees == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        if degrees == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        if degrees == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    @staticmethod
    def _extract_page_number(text: str) -> int:
        """Extract page number from OCR text."""
        for pattern in (PAGE_PATTERN, PAGE_PATTERN_SHORT):
            m = pattern.search(text)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    continue
        return 0

    @staticmethod
    def _score_text(text: str) -> int:
        """Score OCR text quality by counting expected patterns."""
        score = 0
        # Count DNI-like patterns
        score += len(re.findall(r"\bDNI\b", text, re.IGNORECASE)) * 2
        # Count document numbers
        score += len(re.findall(r"\b\d{7,8}\b", text))
        # Count uppercase name-like words
        score += len(re.findall(r"\b[A-ZÁÉÍÓÚÑ]{3,}\b", text))
        return score
