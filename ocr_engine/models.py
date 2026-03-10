"""Data models for the OCR engine module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TipoDocumento(str, Enum):
    """Tipo de documento de identidad."""

    DNI = "DNI"
    LC = "LC"
    LE = "LE"


class DestinoType(str, Enum):
    """Tipos especiales de destino (no-escuela)."""

    JUBILADO = "JUBILADO/A"
    AP_EN_SEDE = "AP. EN SEDE"


@dataclass
class OcrLine:
    """A single line of OCR output with optional metadata."""

    text: str
    confidence: float = 0.0
    bbox: tuple[int, int, int, int] | None = None  # x, y, w, h


@dataclass
class OcrResult:
    """Raw OCR output from any engine."""

    raw_text: str
    lines: list[OcrLine] = field(default_factory=list)
    confidence: float = 0.0
    engine_name: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class PadronRecord:
    """A single parsed record from the electoral roll.

    This is the UNIFIED schema — replaces the 4 different schemas
    that existed across procesar_padron.py (escuela), procesar_tanda.py (escuela),
    process_padron.py (distrito_escuela), and procesar_preparadas.py (destino).
    """

    tipo: str = "DNI"
    documento: str = ""
    nombre: str = ""
    destino: str = ""  # 0-069-XX-XXXX, JUBILADO/A, AP. EN SEDE, or ""
    mesa: int = 0
    confianza: float = 0.0
    observacion: str = ""
    raw: str = ""
    cross_validated: bool = False

    @property
    def has_dni(self) -> bool:
        return len(self.documento) in (7, 8) and self.documento.isdigit()

    @property
    def has_nombre(self) -> bool:
        return len(self.nombre) > 3

    @property
    def has_destino(self) -> bool:
        return self.destino != ""

    @property
    def is_jubilado(self) -> bool:
        return "JUBILAD" in self.destino.upper()

    @property
    def is_ap_en_sede(self) -> bool:
        return "SEDE" in self.destino.upper()


@dataclass
class ProcessingStats:
    """Statistics for a processed page or batch."""

    total_records: int = 0
    filas_esperadas: int = 60
    con_dni: int = 0
    con_nombre: int = 0
    con_destino: int = 0
    alta_confianza: int = 0  # >= 0.7
    media_confianza: int = 0  # 0.3 - 0.7

    @property
    def completitud(self) -> float:
        if self.filas_esperadas == 0:
            return 0.0
        return round(self.total_records / self.filas_esperadas * 100, 1)

    @classmethod
    def from_records(cls, records: list[PadronRecord], filas_esperadas: int = 60) -> ProcessingStats:
        return cls(
            total_records=len(records),
            filas_esperadas=filas_esperadas,
            con_dni=sum(1 for r in records if r.has_dni),
            con_nombre=sum(1 for r in records if r.has_nombre),
            con_destino=sum(1 for r in records if r.has_destino),
            alta_confianza=sum(1 for r in records if r.confianza >= 0.7),
            media_confianza=sum(1 for r in records if 0.3 <= r.confianza < 0.7),
        )


@dataclass
class PageResult:
    """Complete result for a single page."""

    page_number: int = 0
    records: list[PadronRecord] = field(default_factory=list)
    stats: ProcessingStats = field(default_factory=ProcessingStats)
    engine_used: str = ""
    rotation: int = 0
    calidad: str = ""  # BUENA, REGULAR, MALA
    descartadas: list[str] = field(default_factory=list)

    def compute_stats(self, filas_esperadas: int = 60) -> None:
        self.stats = ProcessingStats.from_records(self.records, filas_esperadas)
        if len(self.records) >= 30:
            self.calidad = "BUENA"
        elif len(self.records) >= 15:
            self.calidad = "REGULAR"
        else:
            self.calidad = "MALA"
