"""Google Cloud Vision OCR engine implementation.

Uses the REST API directly (no SDK needed).
Requires GOOGLE_VISION_API_KEY environment variable.

Handles columnar layouts (like padron tables) by reconstructing
rows from word-level bounding boxes.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request
import urllib.error

import cv2
import numpy as np

from ..engine import EngineFactory, OcrEngine
from ..models import OcrLine, OcrResult

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


class GoogleVisionEngine(OcrEngine):
    """OCR engine using Google Cloud Vision REST API.

    Uses DOCUMENT_TEXT_DETECTION for optimal document/table OCR.
    No SDK needed — talks to the REST API via urllib.

    Reconstructs table rows from word bounding boxes so that
    multi-column layouts (DNI | Name | Destino) produce correct
    single-line output per record.
    """

    def __init__(
        self,
        api_key: str | None = None,
        language_hints: list[str] | None = None,
        row_tolerance: int = 20,
    ) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_VISION_API_KEY", "")
        self._language_hints = language_hints or ["es"]
        self._row_tolerance = row_tolerance

    @property
    def name(self) -> str:
        return "google"

    def recognize(self, image: np.ndarray) -> OcrResult:
        """Run Google Vision OCR on a preprocessed image."""
        if not self._api_key:
            raise RuntimeError(
                "GOOGLE_VISION_API_KEY not set. "
                "Export it or pass api_key= to the constructor."
            )

        # Encode image to JPEG base64
        success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not success:
            raise RuntimeError("Failed to encode image to JPEG")
        img_b64 = base64.b64encode(buffer).decode("utf-8")

        # Build request
        request_body = {
            "requests": [
                {
                    "image": {"content": img_b64},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                    "imageContext": {"languageHints": self._language_hints},
                }
            ]
        }

        url = f"{VISION_API_URL}?key={self._api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Google Vision API error {e.code}: {body}") from e

        # Parse response
        api_response = response_data.get("responses", [{}])[0]

        if "error" in api_response:
            err = api_response["error"]
            raise RuntimeError(
                f"Google Vision API error: {err.get('message', str(err))}"
            )

        # Extract data
        full_annotation = api_response.get("fullTextAnnotation", {})
        text_annotations = api_response.get("textAnnotations", [])
        confidence = self._compute_confidence(full_annotation)

        # Reconstruct rows from word bounding boxes
        raw_text, lines = self._reconstruct_rows(
            text_annotations, confidence
        )

        return OcrResult(
            raw_text=raw_text,
            lines=lines,
            confidence=confidence,
            engine_name=self.name,
            metadata={"language_hints": self._language_hints},
        )

    def is_available(self) -> bool:
        return bool(self._api_key or os.environ.get("GOOGLE_VISION_API_KEY"))

    def _reconstruct_rows(
        self,
        text_annotations: list[dict],
        default_confidence: float,
    ) -> tuple[str, list[OcrLine]]:
        """Reconstruct table rows from word-level bounding boxes.

        Google Vision reads columns separately. This method groups words
        by Y-coordinate into rows, then sorts by X within each row,
        producing lines like: "DNI NOMBRE DESTINO".

        Returns:
            Tuple of (raw_text, list of OcrLine).
        """
        if len(text_annotations) < 2:
            # First annotation is the full text, rest are words
            raw = text_annotations[0]["description"] if text_annotations else ""
            return raw, [OcrLine(text=raw, confidence=default_confidence)] if raw else (raw, [])

        # Extract words with top-left coordinates
        words = []
        for annotation in text_annotations[1:]:  # skip first (full text)
            text = annotation.get("description", "").strip()
            if not text:
                continue
            vertices = annotation.get("boundingPoly", {}).get("vertices", [])
            if not vertices:
                continue
            # Use top-left corner for positioning
            x = vertices[0].get("x", 0)
            y = vertices[0].get("y", 0)
            words.append({"text": text, "x": x, "y": y})

        if not words:
            return "", []

        # Sort by Y first, then group into rows
        words.sort(key=lambda w: w["y"])
        rows: list[list[dict]] = []
        current_row: list[dict] = [words[0]]
        current_y = words[0]["y"]

        for word in words[1:]:
            if abs(word["y"] - current_y) <= self._row_tolerance:
                current_row.append(word)
            else:
                rows.append(current_row)
                current_row = [word]
                current_y = word["y"]
        rows.append(current_row)

        # Sort each row by X (left to right) and join
        lines: list[OcrLine] = []
        text_lines: list[str] = []

        for row in rows:
            row.sort(key=lambda w: w["x"])
            line_text = " ".join(w["text"] for w in row)
            if line_text.strip():
                text_lines.append(line_text)
                lines.append(OcrLine(
                    text=line_text,
                    confidence=default_confidence,
                ))

        raw_text = "\n".join(text_lines)
        return raw_text, lines

    @staticmethod
    def _compute_confidence(full_annotation: dict) -> float:
        """Compute average confidence from page/block/paragraph structure."""
        pages = full_annotation.get("pages", [])
        if not pages:
            return 0.0

        confidences = []
        for page in pages:
            for block in page.get("blocks", []):
                conf = block.get("confidence", 0.0)
                if conf > 0:
                    confidences.append(conf)

        return sum(confidences) / len(confidences) if confidences else 0.5


EngineFactory.register("google", GoogleVisionEngine)
