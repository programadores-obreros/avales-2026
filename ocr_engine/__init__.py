"""OCR Engine — Unified OCR module for SUTEBA padron processing."""

from .models import (
    DestinoType,
    OcrLine,
    OcrResult,
    PadronRecord,
    PageResult,
    ProcessingStats,
    TipoDocumento,
)
from .engine import EngineFactory, OcrEngine

__all__ = [
    "DestinoType",
    "EngineFactory",
    "OcrEngine",
    "OcrLine",
    "OcrResult",
    "PadronRecord",
    "PageResult",
    "ProcessingStats",
    "TipoDocumento",
]
