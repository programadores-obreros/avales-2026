"""PaddleOCR engine implementation."""

from __future__ import annotations

import numpy as np

from ..engine import EngineFactory, OcrEngine
from ..models import OcrLine, OcrResult


class PaddleOcrEngine(OcrEngine):
    """OCR engine using PaddleOCR.

    PaddleOCR provides both text detection and recognition,
    with good support for tabular documents.
    """

    def __init__(
        self,
        lang: str = "es",
        use_gpu: bool = False,
        det_model_dir: str | None = None,
        rec_model_dir: str | None = None,
    ) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._det_model_dir = det_model_dir
        self._rec_model_dir = rec_model_dir
        self._ocr = None  # Lazy init

    def _get_ocr(self):
        """Lazy-initialize PaddleOCR instance (downloads models on first run)."""
        if self._ocr is None:
            from paddleocr import PaddleOCR

            kwargs = {
                "use_angle_cls": True,
                "lang": self._lang,
                "use_gpu": self._use_gpu,
                "show_log": False,
            }
            if self._det_model_dir:
                kwargs["det_model_dir"] = self._det_model_dir
            if self._rec_model_dir:
                kwargs["rec_model_dir"] = self._rec_model_dir

            self._ocr = PaddleOCR(**kwargs)
        return self._ocr

    @property
    def name(self) -> str:
        return "paddle"

    def recognize(self, image: np.ndarray) -> OcrResult:
        """Run PaddleOCR on a preprocessed image.

        PaddleOCR returns: list[list[ [box_points], (text, confidence) ]]
        We convert this to our OcrResult format.
        """
        ocr = self._get_ocr()
        result = ocr.ocr(image, cls=True)

        lines: list[OcrLine] = []
        raw_lines: list[str] = []
        total_conf = 0.0

        if result and result[0]:
            for detection in result[0]:
                box_points = detection[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                text, conf = detection[1]

                # Convert box points to x, y, w, h
                xs = [p[0] for p in box_points]
                ys = [p[1] for p in box_points]
                x = int(min(xs))
                y = int(min(ys))
                w = int(max(xs) - x)
                h = int(max(ys) - y)

                lines.append(
                    OcrLine(text=text.strip(), confidence=conf, bbox=(x, y, w, h))
                )
                raw_lines.append(text.strip())
                total_conf += conf

        raw_text = "\n".join(raw_lines)
        overall_conf = total_conf / len(lines) if lines else 0.0

        return OcrResult(
            raw_text=raw_text,
            lines=lines,
            confidence=overall_conf,
            engine_name=self.name,
        )

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401

            return True
        except ImportError:
            return False


EngineFactory.register("paddle", PaddleOcrEngine)
