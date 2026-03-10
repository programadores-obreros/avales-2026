"""Tests for OCR engine contracts and factory."""

import numpy as np
import pytest

# Ensure engines are registered before tests run
import ocr_engine.engines  # noqa: F401
from ocr_engine.engine import EngineFactory, OcrEngine
from ocr_engine.models import OcrResult


def _tesseract_available() -> bool:
    try:
        from ocr_engine.engines.tesseract import TesseractEngine
        return TesseractEngine().is_available()
    except Exception:
        return False


# ============================================================
# Factory tests
# ============================================================

class TestEngineFactory:

    def test_tesseract_registered(self):
        assert "tesseract" in EngineFactory.registered()

    def test_claude_registered(self):
        assert "claude" in EngineFactory.registered()

    def test_paddle_registered(self):
        assert "paddle" in EngineFactory.registered()

    def test_create_tesseract(self):
        engine = EngineFactory.create("tesseract")
        assert isinstance(engine, OcrEngine)
        assert engine.name == "tesseract"

    def test_create_unknown_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            EngineFactory.create("nonexistent_engine")

    def test_available_returns_list(self):
        available = EngineFactory.available()
        assert isinstance(available, list)


# ============================================================
# Tesseract engine contract
# ============================================================

class TestTesseractEngine:

    @pytest.fixture
    def engine(self):
        from ocr_engine.engines.tesseract import TesseractEngine
        return TesseractEngine()

    def test_name(self, engine):
        assert engine.name == "tesseract"

    @pytest.mark.skipif(not _tesseract_available(), reason="Tesseract not installed")
    def test_is_available(self, engine):
        assert engine.is_available()

    @pytest.mark.skipif(not _tesseract_available(), reason="Tesseract not installed")
    def test_recognize_returns_ocr_result(self, engine):
        img = np.full((100, 300), 255, dtype=np.uint8)
        result = engine.recognize(img)
        assert isinstance(result, OcrResult)
        assert result.engine_name == "tesseract"
        assert 0.0 <= result.confidence <= 1.0


# ============================================================
# Claude engine contract (without actual API call)
# ============================================================

class TestClaudeEngine:

    @pytest.fixture
    def engine(self):
        from ocr_engine.engines.claude import ClaudeVisionEngine
        return ClaudeVisionEngine()

    def test_name(self, engine):
        assert engine.name == "claude"

    def test_is_available_checks_api_key(self, engine, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert not engine.is_available()


# ============================================================
# PaddleOCR engine contract (skip if not installed)
# ============================================================

class TestPaddleEngine:

    @pytest.fixture
    def engine(self):
        from ocr_engine.engines.paddle import PaddleOcrEngine
        return PaddleOcrEngine()

    def test_name(self, engine):
        assert engine.name == "paddle"

    def test_is_available(self, engine):
        result = engine.is_available()
        assert isinstance(result, bool)
