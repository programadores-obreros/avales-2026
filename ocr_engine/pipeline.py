"""OCR processing pipelines — single image and hybrid.

Usage:
    pipeline = SingleImagePipeline.with_tesseract("069")
    result = pipeline.process("path/to/image.jpg")
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .engine import OcrEngine
from .models import PageResult, PadronRecord
from .parsing.parser import PadronParser
from .preprocessing.pipeline import PreprocessingPipeline
from .preprocessing.steps import ExifCorrector


class SingleImagePipeline:
    """Full OCR pipeline: load → preprocess → OCR → parse → PageResult.

    Replaces the main flow of procesar_padron.py.
    """

    def __init__(
        self,
        engine: OcrEngine,
        preprocessing: PreprocessingPipeline,
        parser: PadronParser,
        min_confianza: float = 0.3,
    ) -> None:
        self._engine = engine
        self._preprocessing = preprocessing
        self._parser = parser
        self._min_confianza = min_confianza

    def process(
        self,
        image_path: str,
        page_num: int = 0,
        debug: bool = False,
    ) -> PageResult:
        """Process a single image through the full pipeline.

        Args:
            image_path: Path to the image file.
            page_num: Page number for context.
            debug: If True, save intermediate images.

        Returns:
            PageResult with parsed records and stats.
        """
        # 1. Load with EXIF correction
        img = ExifCorrector.from_file(image_path)

        # 2. Preprocess
        processed = self._preprocessing.process(img, debug=debug)

        # 3. OCR
        ocr_result = self._engine.recognize(processed)

        # 4. Parse
        records = self._parser.parse_page(ocr_result.raw_text, page_num=page_num)

        # 5. Filter by confidence
        filtered = [r for r in records if r.confianza >= self._min_confianza]
        descartadas = [
            r.raw for r in records if r.confianza < self._min_confianza and r.raw
        ]

        # 6. Build result
        result = PageResult(
            page_number=page_num,
            records=filtered,
            engine_used=self._engine.name,
            descartadas=descartadas,
        )
        result.compute_stats()

        return result

    def process_array(
        self,
        image: np.ndarray,
        page_num: int = 0,
        debug: bool = False,
    ) -> PageResult:
        """Process an already-loaded image array.

        Args:
            image: OpenCV image (BGR or grayscale).
            page_num: Page number for context.
            debug: If True, save intermediate images.

        Returns:
            PageResult with parsed records and stats.
        """
        processed = self._preprocessing.process(image, debug=debug)
        ocr_result = self._engine.recognize(processed)
        records = self._parser.parse_page(ocr_result.raw_text, page_num=page_num)

        filtered = [r for r in records if r.confianza >= self._min_confianza]
        descartadas = [
            r.raw for r in records if r.confianza < self._min_confianza and r.raw
        ]

        result = PageResult(
            page_number=page_num,
            records=filtered,
            engine_used=self._engine.name,
            descartadas=descartadas,
        )
        result.compute_stats()
        return result

    @classmethod
    def with_tesseract(
        cls, distrito: str = "069", psm: int = 4, **kwargs
    ) -> SingleImagePipeline:
        """Create a pipeline with Tesseract engine and default preprocessing."""
        from .engines.tesseract import TesseractEngine

        return cls(
            engine=TesseractEngine(psm=psm),
            preprocessing=PreprocessingPipeline.default_tesseract(),
            parser=PadronParser(distrito),
            **kwargs,
        )

    @classmethod
    def with_claude(
        cls, distrito: str = "069", pagina: int | None = None, **kwargs
    ) -> SingleImagePipeline:
        """Create a pipeline with Claude Vision engine and light preprocessing."""
        from .engines.claude import ClaudeVisionEngine

        return cls(
            engine=ClaudeVisionEngine(pagina=pagina),
            preprocessing=PreprocessingPipeline.default_vision(),
            parser=PadronParser(distrito),
            **kwargs,
        )


class HybridPipeline:
    """Multi-engine pipeline with fallback and cross-validation.

    Strategy:
    1. Run primary engine (Tesseract/PaddleOCR)
    2. If confidence < confidence_threshold, run fallback engine
    3. If both ran, cross-validate results
    4. If confidence still < vision_threshold, use Claude Vision (expensive)

    Cost optimization: Claude Vision only called when really needed.
    """

    def __init__(
        self,
        primary: OcrEngine,
        fallback: OcrEngine | None = None,
        vision: OcrEngine | None = None,
        parser: PadronParser | None = None,
        preprocessing: PreprocessingPipeline | None = None,
        confidence_threshold: float = 0.6,
        vision_threshold: float = 0.4,
        min_confianza: float = 0.3,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._vision = vision
        self._parser = parser or PadronParser("069")
        self._preprocessing = preprocessing or PreprocessingPipeline.default_tesseract()
        self._confidence_threshold = confidence_threshold
        self._vision_threshold = vision_threshold
        self._min_confianza = min_confianza

    def process(
        self,
        image: np.ndarray,
        page_num: int = 0,
        debug: bool = False,
    ) -> PageResult:
        """Process an image through the hybrid pipeline."""
        from .validator import CrossValidator

        processed = self._preprocessing.process(image, debug=debug)
        engine_results: dict[str, list[PadronRecord]] = {}

        # Step 1: Primary engine
        primary_result = self._primary.recognize(processed)
        primary_records = self._parser.parse_page(primary_result.raw_text, page_num)
        engine_results[self._primary.name] = primary_records
        engines_used = [self._primary.name]

        # Step 2: Fallback if confidence too low
        if primary_result.confidence < self._confidence_threshold and self._fallback:
            fallback_result = self._fallback.recognize(processed)
            fallback_records = self._parser.parse_page(fallback_result.raw_text, page_num)
            engine_results[self._fallback.name] = fallback_records
            engines_used.append(self._fallback.name)

        # Step 3: Vision if still too low
        best_confidence = primary_result.confidence
        if (
            best_confidence < self._vision_threshold
            and self._vision
            and self._vision.is_available()
        ):
            vision_result = self._vision.recognize(processed)
            vision_records = self._parser.parse_page(vision_result.raw_text, page_num)
            engine_results[self._vision.name] = vision_records
            engines_used.append(self._vision.name)

        # Step 4: Cross-validate if multiple engines ran
        if len(engine_results) > 1:
            validator = CrossValidator()
            merged = validator.validate(engine_results)
        else:
            merged = list(engine_results.values())[0]

        # Filter
        filtered = [r for r in merged if r.confianza >= self._min_confianza]

        result = PageResult(
            page_number=page_num,
            records=filtered,
            engine_used="+".join(engines_used),
        )
        result.compute_stats()
        return result
