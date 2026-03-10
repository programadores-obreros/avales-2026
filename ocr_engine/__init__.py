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
from .parsing.parser import PadronParser
from .parsing.sanitizer import LineSanitizer
from .pipeline import SingleImagePipeline
from .output import OutputWriter

__all__ = [
    "DestinoType",
    "EngineFactory",
    "LineSanitizer",
    "OcrEngine",
    "OcrLine",
    "OcrResult",
    "OutputWriter",
    "PadronParser",
    "PadronRecord",
    "PageResult",
    "ProcessingStats",
    "SingleImagePipeline",
    "TipoDocumento",
]
