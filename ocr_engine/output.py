"""Output writers — JSON, CSV, XLSX export for OCR results."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import PageResult, PadronRecord


class OutputWriter:
    """Write OCR results to various formats."""

    @staticmethod
    def to_json(
        records: list[PadronRecord],
        path: str | Path,
        page_result: PageResult | None = None,
    ) -> None:
        """Write records to JSON file.

        Matches the existing format from procesar_padron.py:
        {pagina, total_registros, filas_esperadas, completitud, registros, stats}
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        registros = [
            {
                "tipo": r.tipo,
                "documento": r.documento,
                "nombre": r.nombre,
                "destino": r.destino,
                "mesa": r.mesa,
                "confianza": r.confianza,
                "raw": r.raw,
            }
            for r in records
        ]

        data: dict = {"registros": registros, "total_registros": len(registros)}

        if page_result:
            data["pagina"] = page_result.page_number
            data["filas_esperadas"] = page_result.stats.filas_esperadas
            data["completitud"] = page_result.stats.completitud
            data["calidad"] = page_result.calidad
            data["engine"] = page_result.engine_used
            data["stats"] = {
                "con_dni": page_result.stats.con_dni,
                "con_nombre": page_result.stats.con_nombre,
                "con_destino": page_result.stats.con_destino,
                "alta_confianza": page_result.stats.alta_confianza,
                "media_confianza": page_result.stats.media_confianza,
            }
            data["descartadas"] = page_result.descartadas

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(records: list[PadronRecord], path: str | Path) -> None:
        """Write records to CSV file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["TIPO", "DOCUMENTO", "NOMBRE", "DESTINO", "MESA", "CONFIANZA"])
            for r in records:
                writer.writerow([r.tipo, r.documento, r.nombre, r.destino, r.mesa, r.confianza])

    @staticmethod
    def to_xlsx(records: list[PadronRecord], path: str | Path) -> None:
        """Write records to Excel file. Requires openpyxl."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Padron"
            ws.append(["TIPO", "DOCUMENTO", "NOMBRE", "DESTINO", "MESA", "CONFIANZA"])
            for r in records:
                ws.append([r.tipo, r.documento, r.nombre, r.destino, r.mesa, r.confianza])
            wb.save(str(path))
        except ImportError:
            raise ImportError("openpyxl is required for XLSX export: pip install openpyxl")
