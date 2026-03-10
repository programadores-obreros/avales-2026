"""Tesseract OCR engine implementation."""

from __future__ import annotations

import numpy as np

from ..engine import EngineFactory, OcrEngine
from ..models import OcrLine, OcrResult


class TesseractEngine(OcrEngine):
    """OCR engine using pytesseract (Tesseract wrapper).

    Extracted from 13_mayo_2026/padron_provisorio/procesar_padron.py
    and pradones/process_padron.py.
    """

    def __init__(self, psm: int = 4, lang: str = "spa", oem: int = 3) -> None:
        self._psm = psm
        self._lang = lang
        self._oem = oem

    @property
    def name(self) -> str:
        return "tesseract"

    def recognize(self, image: np.ndarray) -> OcrResult:
        """Run Tesseract OCR on a preprocessed image.

        Args:
            image: OpenCV image (BGR or grayscale numpy array).

        Returns:
            OcrResult with raw text, parsed lines, and confidence.
        """
        import pytesseract

        config = f"--oem {self._oem} --psm {self._psm} -c preserve_interword_spaces=1"

        # Get raw text
        raw_text = pytesseract.image_to_string(image, lang=self._lang, config=config)

        # Get per-line confidence from image_to_data
        lines: list[OcrLine] = []
        total_conf = 0.0
        conf_count = 0

        try:
            data = pytesseract.image_to_data(
                image, lang=self._lang, config=config, output_type=pytesseract.Output.DICT
            )
            current_line_num = -1
            current_line_text = ""
            current_line_confs: list[float] = []
            current_bbox: list[int] = [0, 0, 0, 0]  # x, y, w, h

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])
                line_num = data["line_num"][i]

                if line_num != current_line_num:
                    # Save previous line
                    if current_line_text.strip():
                        avg_conf = (
                            sum(current_line_confs) / len(current_line_confs)
                            if current_line_confs
                            else 0.0
                        )
                        lines.append(
                            OcrLine(
                                text=current_line_text.strip(),
                                confidence=avg_conf / 100.0,
                                bbox=tuple(current_bbox),
                            )
                        )
                        total_conf += avg_conf
                        conf_count += 1

                    current_line_num = line_num
                    current_line_text = ""
                    current_line_confs = []
                    current_bbox = [
                        data["left"][i],
                        data["top"][i],
                        data["width"][i],
                        data["height"][i],
                    ]

                if text and conf > 0:
                    current_line_text += " " + text if current_line_text else text
                    current_line_confs.append(conf)
                    # Expand bbox
                    x2 = max(current_bbox[0] + current_bbox[2], data["left"][i] + data["width"][i])
                    y2 = max(current_bbox[1] + current_bbox[3], data["top"][i] + data["height"][i])
                    current_bbox[0] = min(current_bbox[0], data["left"][i])
                    current_bbox[1] = min(current_bbox[1], data["top"][i])
                    current_bbox[2] = x2 - current_bbox[0]
                    current_bbox[3] = y2 - current_bbox[1]

            # Don't forget the last line
            if current_line_text.strip():
                avg_conf = (
                    sum(current_line_confs) / len(current_line_confs)
                    if current_line_confs
                    else 0.0
                )
                lines.append(
                    OcrLine(
                        text=current_line_text.strip(),
                        confidence=avg_conf / 100.0,
                        bbox=tuple(current_bbox),
                    )
                )
                total_conf += avg_conf
                conf_count += 1

        except Exception:
            # Fallback: parse raw text into lines without confidence
            for line_text in raw_text.strip().split("\n"):
                stripped = line_text.strip()
                if stripped:
                    lines.append(OcrLine(text=stripped))

        overall_confidence = (total_conf / conf_count / 100.0) if conf_count > 0 else 0.0

        return OcrResult(
            raw_text=raw_text,
            lines=lines,
            confidence=overall_confidence,
            engine_name=self.name,
        )

    def is_available(self) -> bool:
        try:
            import pytesseract

            version = pytesseract.get_tesseract_version()
            return version is not None
        except Exception:
            return False


EngineFactory.register("tesseract", TesseractEngine)
