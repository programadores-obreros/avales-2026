"""Tests for SingleImagePipeline and HybridPipeline."""

import numpy as np
import pytest

from ocr_engine.engine import OcrEngine
from ocr_engine.models import OcrLine, OcrResult, PageResult, PadronRecord
from ocr_engine.parsing.parser import PadronParser
from ocr_engine.pipeline import HybridPipeline, SingleImagePipeline
from ocr_engine.preprocessing.pipeline import PreprocessingPipeline


# ============================================================
# Mock engine for testing
# ============================================================

class MockEngine(OcrEngine):
    """Mock OCR engine that returns predefined text."""

    def __init__(self, raw_text: str = "", confidence: float = 0.8, engine_name: str = "mock"):
        self._raw_text = raw_text
        self._confidence = confidence
        self._engine_name = engine_name

    @property
    def name(self) -> str:
        return self._engine_name

    def recognize(self, image: np.ndarray) -> OcrResult:
        lines = [OcrLine(text=l.strip()) for l in self._raw_text.split("\n") if l.strip()]
        return OcrResult(
            raw_text=self._raw_text,
            lines=lines,
            confidence=self._confidence,
            engine_name=self._engine_name,
        )

    def is_available(self) -> bool:
        return True


# ============================================================
# SingleImagePipeline tests
# ============================================================

class TestSingleImagePipeline:

    def test_process_array(self):
        ocr_text = """DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 1
DNI 14009185 PEREZ JUAN  0-069-MS-0042 1"""

        pipeline = SingleImagePipeline(
            engine=MockEngine(raw_text=ocr_text),
            preprocessing=PreprocessingPipeline(),  # Empty pipeline
            parser=PadronParser("069"),
        )

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = pipeline.process_array(img, page_num=1)

        assert isinstance(result, PageResult)
        assert len(result.records) == 2
        assert result.records[0].documento == "27241872"
        assert result.records[1].documento == "14009185"
        assert result.engine_used == "mock"
        assert result.calidad in ("BUENA", "REGULAR", "MALA")

    def test_confidence_filter(self):
        # Text that produces low-confidence results only
        ocr_text = "RANDOM GARBAGE TEXT"

        pipeline = SingleImagePipeline(
            engine=MockEngine(raw_text=ocr_text),
            preprocessing=PreprocessingPipeline(),
            parser=PadronParser("069"),
            min_confianza=0.5,
        )

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = pipeline.process_array(img, page_num=1)
        # Should filter out low-confidence records
        assert all(r.confianza >= 0.5 for r in result.records)


# ============================================================
# HybridPipeline tests
# ============================================================

class TestHybridPipeline:

    def test_primary_only_high_confidence(self):
        """High confidence → no fallback triggered."""
        primary = MockEngine(
            raw_text="DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 1",
            confidence=0.9,
            engine_name="primary",
        )
        fallback = MockEngine(
            raw_text="DNI 99999999 NOBODY  0-069-XX-0000 1",
            confidence=0.5,
            engine_name="fallback",
        )

        pipeline = HybridPipeline(
            primary=primary,
            fallback=fallback,
            confidence_threshold=0.6,
        )

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = pipeline.process(img, page_num=1)

        assert "primary" in result.engine_used
        assert "fallback" not in result.engine_used

    def test_fallback_triggered(self):
        """Low confidence → fallback triggered."""
        primary = MockEngine(
            raw_text="DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 1",
            confidence=0.3,
            engine_name="primary",
        )
        fallback = MockEngine(
            raw_text="DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 1",
            confidence=0.8,
            engine_name="fallback",
        )

        pipeline = HybridPipeline(
            primary=primary,
            fallback=fallback,
            confidence_threshold=0.6,
        )

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = pipeline.process(img, page_num=1)

        assert "primary" in result.engine_used
        assert "fallback" in result.engine_used

    def test_no_fallback_configured(self):
        """No fallback engine → just use primary."""
        primary = MockEngine(
            raw_text="DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 1",
            confidence=0.3,
            engine_name="primary",
        )

        pipeline = HybridPipeline(primary=primary, confidence_threshold=0.6)

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = pipeline.process(img, page_num=1)
        assert result.engine_used == "primary"
