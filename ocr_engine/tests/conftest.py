"""Shared pytest fixtures for ocr_engine tests."""

import numpy as np
import pytest

from ocr_engine.models import PadronRecord
from ocr_engine.parsing.parser import PadronParser
from ocr_engine.parsing.sanitizer import LineSanitizer


# ============================================================
# Sanitizer / Parser fixtures
# ============================================================

@pytest.fixture
def sanitizer_069() -> LineSanitizer:
    """LineSanitizer for distrito 069 (La Matanza)."""
    return LineSanitizer("069")


@pytest.fixture
def sanitizer_base() -> LineSanitizer:
    """LineSanitizer with base rules only."""
    return LineSanitizer()


@pytest.fixture
def parser_069() -> PadronParser:
    """PadronParser for distrito 069 (La Matanza)."""
    return PadronParser("069")


@pytest.fixture
def parser_base() -> PadronParser:
    """PadronParser with base rules only."""
    return PadronParser()


# ============================================================
# Image fixtures (synthetic)
# ============================================================

@pytest.fixture
def gray_100x100() -> np.ndarray:
    """100x100 grayscale image with random variation."""
    return np.random.randint(50, 200, (100, 100), dtype=np.uint8)


@pytest.fixture
def bgr_100x100() -> np.ndarray:
    """100x100 BGR image with random variation."""
    return np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def white_image() -> np.ndarray:
    """200x300 white grayscale image (blank page)."""
    return np.full((200, 300), 255, dtype=np.uint8)


@pytest.fixture
def content_image() -> np.ndarray:
    """200x200 BGR image with a black square in center (simulates content)."""
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    img[50:150, 50:150] = 0
    return img


# ============================================================
# OCR text fixtures
# ============================================================

SAMPLE_OCR_PAGE = """\
MESA: 5
DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 5
DNI 14009185 PEREZ JUAN  0-069-MS-0042 5
DNI 17257008 ZARATE SONIA BEATRIZ  JUBILADO/A 5
DNI 32456789 GONZALEZ MARIA ANA  0-069-EE-0501 5
DNI 22334455 LOPEZ MARTINEZ ANA  AP. EN SEDE 5
"""


@pytest.fixture
def sample_ocr_text() -> str:
    """Sample OCR page text with 5 records."""
    return SAMPLE_OCR_PAGE


# ============================================================
# Expected records fixtures
# ============================================================

@pytest.fixture
def expected_records() -> list[PadronRecord]:
    """Known-good records matching sample_ocr_text."""
    return [
        PadronRecord(tipo="DNI", documento="27241872", nombre="VILLAFAÑE JORGE",
                     destino="0-069-MT-0001", mesa=5, confianza=0.7),
        PadronRecord(tipo="DNI", documento="14009185", nombre="PEREZ JUAN",
                     destino="0-069-MS-0042", mesa=5, confianza=0.7),
        PadronRecord(tipo="DNI", documento="17257008", nombre="ZARATE SONIA BEATRIZ",
                     destino="JUBILADO/A", mesa=5, confianza=0.7),
        PadronRecord(tipo="DNI", documento="32456789", nombre="GONZALEZ MARIA ANA",
                     destino="0-069-EE-0501", mesa=5, confianza=0.7),
        PadronRecord(tipo="DNI", documento="22334455", nombre="LOPEZ MARTINEZ ANA",
                     destino="AP. EN SEDE", mesa=5, confianza=0.7),
    ]
