"""Padron line parser — extracts structured records from OCR text.

Extracted from pradones/process_padron.py:parse_line() and
13_mayo_2026/padron_provisorio/procesar_padron.py:parsear_linea().
"""

from __future__ import annotations

import re

from ..models import PadronRecord
from .sanitizer import LineSanitizer

# Trailing OCR garbage absorber
_TRAIL = r"[\s\S]*$"

# Ordered patterns from most specific to most flexible.
# Each captures: (TIPO, DOCUMENTO, NOMBRE, DESTINO, MESA)
PATTERNS = [
    # Standard establishment code: 0-069-MS-0042
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+"
        rf"([\d]-[\d]{{2,3}}-[A-Z]{{2}}-[\d]{{3,4}})\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Establishment code with OCR variations (O instead of 0)
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+"
        rf"([O\d]-[O\d]{{2,3}}-[A-Z\d]{{2}}-[O\d]{{3,4}})\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # JUBILADO/A
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}"
        rf"(JUBILAD\S*/?\s*A)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # AP. EN SEDE
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}"
        rf"(AP\.?\s*EN\s*SEDE)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # TITULAR / SUPLENTE
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}"
        rf"(TITULAR|SUPLENTE)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Fallback: any uppercase text block before a trailing number
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}"
        rf"([A-Z][A-Z\s./]{{2,}}?)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Last resort: known destinos with single-space sep
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+"
        rf"(JUBILAD\S*/?\s*A|AP\.?\s*EN\s*SEDE)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Ultra-fallback: establishment code with single space
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+"
        rf"([\dO]-[\dO]{{2,3}}-[A-Z\d]{{2}}-[\dO]{{3,4}})\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
]

# Rescue pattern: TIPO+DOC+NAME+DESTINO but mesa number is garbled
RESCUE_PATTERN = re.compile(
    r"^(DNI|L[CE])\.?\s+(\d{4,9})\.?\s+(.+?)\s+"
    r"(JUBILAD\S*/?\s*\S*|AP\.?\s*EN\s*SEDE|[\dO]-[\dO]{2,3}-[A-Z\d]{2}-[\dO]{3,4})",
    re.IGNORECASE,
)

# Detect MESA section headers
MESA_HEADER = re.compile(r"MESA[:\s]+(\d+)[:\s]*(.*)", re.IGNORECASE)

# Detect lines that START like data but failed to parse
PARTIAL_LINE = re.compile(r"^(DNI|L[CE])\s+\d", re.IGNORECASE)

# Simple DNI extractor (for procesar_padron.py style parsing)
DNI_SIMPLE = re.compile(r"\b(\d{7,8})\b")

# Simple school code extractor
ESCUELA_SIMPLE = re.compile(r"(0-0\d{2}-[A-Z]{1,2}-\d{4})")

# Uppercase name block
NOMBRE_PATTERN = re.compile(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{4,}")


def _normalize_destino(raw: str) -> str:
    """Normalize DESTINO values for OCR inconsistencies."""
    upper = raw.upper().strip()
    if "JUBILAD" in upper:
        return "JUBILADO/A"
    if "SEDE" in upper:
        return "AP. EN SEDE"
    if re.match(r"^[\dO]-[\dO]{2,3}-[A-Z\d]{2}-[\dO]{3,4}$", upper):
        return upper.replace("O", "0")
    return upper


def _clean_nombre(raw: str) -> str:
    """Clean extracted name: remove DNI/destino words, extra spaces."""
    nombre = raw.strip()
    nombre = re.sub(r"\b(DNI|JUBILADO/?A?|AP\s*EN\s*SEDE)\b", "", nombre)
    nombre = re.sub(r"\b\d+\b", "", nombre)
    nombre = re.sub(r"\s{2,}", " ", nombre)
    return nombre.strip()


class PadronParser:
    """Parses OCR text lines into PadronRecord instances.

    Supports two modes:
    - Full mode (from process_padron.py): regex patterns with mesa tracking
    - Simple mode (from procesar_padron.py): DNI + nombre + escuela extraction

    Usage:
        parser = PadronParser("069")
        record = parser.parse_line("DNI 27241872 VILLAFAÑE JORGE 0-069-MT-0001 1")
        records = parser.parse_page(ocr_text, page_num=42)
    """

    def __init__(self, distrito: str | None = None) -> None:
        self._sanitizer = LineSanitizer(distrito)

    def parse_line(self, line: str, last_mesa: int = 1) -> PadronRecord | None:
        """Parse a single OCR line into a PadronRecord.

        Uses the full regex pattern set from process_padron.py.
        Falls back to simple extraction if full patterns don't match.

        Args:
            line: Raw OCR text line.
            last_mesa: Last known mesa number for rescue parsing.

        Returns:
            PadronRecord or None if the line can't be parsed.
        """
        cleaned = self._sanitizer.sanitize(line)
        if not cleaned or len(cleaned) < 10:
            return None

        # Try full patterns first (process_padron.py style)
        for pattern in PATTERNS:
            m = pattern.match(cleaned)
            if m:
                return PadronRecord(
                    tipo=m.group(1).upper(),
                    documento=re.sub(r"[^\d]", "", m.group(2)),
                    nombre=m.group(3).strip(),
                    destino=_normalize_destino(m.group(4)),
                    mesa=int(m.group(5)),
                    confianza=0.7,
                    raw=line.strip(),
                )

        # Rescue: matched TIPO+DOC+NAME+DESTINO but mesa is garbled
        m = RESCUE_PATTERN.match(cleaned)
        if m:
            return PadronRecord(
                tipo=m.group(1).upper(),
                documento=re.sub(r"[^\d]", "", m.group(2)),
                nombre=m.group(3).strip(),
                destino=_normalize_destino(m.group(4)),
                mesa=last_mesa,
                confianza=0.5,
                raw=line.strip(),
            )

        # Fallback: simple extraction (procesar_padron.py style)
        return self._parse_simple(cleaned, line.strip())

    def _parse_simple(self, cleaned: str, raw: str) -> PadronRecord | None:
        """Simple extraction: find DNI, nombre, escuela independently."""
        confianza = 0.0

        # DNI
        documento = ""
        dni_match = DNI_SIMPLE.search(cleaned)
        if dni_match:
            documento = dni_match.group(1)
            confianza += 0.3

        # Escuela/destino
        destino = ""
        escuela_match = ESCUELA_SIMPLE.search(cleaned)
        if escuela_match:
            destino = escuela_match.group(1)
            confianza += 0.3
        elif re.search(r"JUBILADO/?A?", cleaned, re.IGNORECASE):
            destino = "JUBILADO/A"
            confianza += 0.25
        elif re.search(r"AP\.?\s*EN\s*SEDE", cleaned, re.IGNORECASE):
            destino = "AP. EN SEDE"
            confianza += 0.2

        # Nombre
        nombre = ""
        nombre_match = NOMBRE_PATTERN.search(cleaned)
        if nombre_match:
            nombre = _clean_nombre(nombre_match.group(0))
            if len(nombre) > 3:
                confianza += 0.4

        if confianza < 0.3:
            return None

        # Detect tipo
        tipo = "DNI"
        if re.match(r"^LC\b", cleaned, re.IGNORECASE):
            tipo = "LC"
        elif re.match(r"^LE\b", cleaned, re.IGNORECASE):
            tipo = "LE"

        return PadronRecord(
            tipo=tipo,
            documento=documento,
            nombre=nombre,
            destino=destino,
            confianza=confianza,
            raw=raw,
        )

    def parse_page(self, text: str, page_num: int = 0) -> list[PadronRecord]:
        """Parse a full page of OCR text into records.

        Args:
            text: Raw OCR text (newline-separated lines).
            page_num: Page number for context.

        Returns:
            List of successfully parsed PadronRecord instances.
        """
        lines = text.strip().split("\n")
        records: list[PadronRecord] = []
        last_mesa = 1

        for line in lines:
            # Check for MESA header
            mesa_match = MESA_HEADER.search(line)
            if mesa_match:
                last_mesa = int(mesa_match.group(1))
                continue

            record = self.parse_line(line, last_mesa=last_mesa)
            if record:
                if record.mesa > 0:
                    last_mesa = record.mesa
                records.append(record)

        return records

    def is_partial_line(self, line: str) -> bool:
        """Check if a line starts like data but couldn't be parsed."""
        return bool(PARTIAL_LINE.match(line.strip()))
