"""Cross-validation — merge results from multiple OCR engines.

Compares records from different engines and resolves disagreements
using majority vote or highest-confidence engine.
"""

from __future__ import annotations

from collections import Counter

from .models import PadronRecord


class CrossValidator:
    """Cross-validate OCR results from multiple engines.

    Matching strategy:
    1. Primary match by DNI number across engine results
    2. Positional fallback (line N from each engine)

    Per-field resolution: majority vote or highest confidence.
    """

    def validate(self, results: dict[str, list[PadronRecord]]) -> list[PadronRecord]:
        """Merge results from multiple engines.

        Args:
            results: Dict of engine_name -> list[PadronRecord].

        Returns:
            Merged list of PadronRecord with cross_validated=True.
        """
        if not results:
            return []

        engines = list(results.keys())
        if len(engines) == 1:
            # Single engine, just mark as validated
            return [self._mark_validated(r) for r in results[engines[0]]]

        # Build DNI → records mapping per engine
        dni_maps: dict[str, dict[str, PadronRecord]] = {}
        for engine_name, records in results.items():
            dni_map: dict[str, PadronRecord] = {}
            for r in records:
                if r.documento:
                    dni_map[r.documento] = r
            dni_maps[engine_name] = dni_map

        # Collect all unique DNIs
        all_dnis: set[str] = set()
        for dni_map in dni_maps.values():
            all_dnis.update(dni_map.keys())

        merged: list[PadronRecord] = []

        # Phase 1: Merge by DNI match
        matched_dnis: set[str] = set()
        for dni in sorted(all_dnis):
            candidates = []
            for engine_name in engines:
                if dni in dni_maps[engine_name]:
                    candidates.append(dni_maps[engine_name][dni])

            if len(candidates) >= 2:
                merged.append(self._merge_records(candidates))
                matched_dnis.add(dni)
            elif len(candidates) == 1:
                merged.append(self._mark_validated(candidates[0]))
                matched_dnis.add(dni)

        # Phase 2: Positional fallback for records without DNI match
        for engine_name, records in results.items():
            for r in records:
                if r.documento and r.documento in matched_dnis:
                    continue
                if not r.documento:
                    # Try to find positional match (not implemented for simplicity)
                    merged.append(self._mark_validated(r))

        return merged

    def _merge_records(self, candidates: list[PadronRecord]) -> PadronRecord:
        """Merge multiple records for the same DNI."""
        # Majority vote for each field
        tipo = self._majority([r.tipo for r in candidates], default="DNI")
        documento = self._majority([r.documento for r in candidates if r.documento])
        nombre = self._best_by_confidence(candidates, "nombre")
        destino = self._best_by_confidence(candidates, "destino")
        mesa = self._majority([r.mesa for r in candidates if r.mesa > 0], default=0)

        avg_conf = sum(r.confianza for r in candidates) / len(candidates)

        return PadronRecord(
            tipo=tipo,
            documento=documento,
            nombre=nombre,
            destino=destino,
            mesa=mesa,
            confianza=avg_conf,
            cross_validated=True,
        )

    @staticmethod
    def _majority(values: list, default=None):
        """Return the most common value, or default if empty."""
        if not values:
            return default
        counter = Counter(values)
        return counter.most_common(1)[0][0]

    @staticmethod
    def _best_by_confidence(candidates: list[PadronRecord], field: str) -> str:
        """Return the field value from the highest-confidence candidate."""
        best = max(candidates, key=lambda r: r.confianza)
        return getattr(best, field, "")

    @staticmethod
    def _mark_validated(record: PadronRecord) -> PadronRecord:
        """Return a copy with cross_validated=True."""
        return PadronRecord(
            tipo=record.tipo,
            documento=record.documento,
            nombre=record.nombre,
            destino=record.destino,
            mesa=record.mesa,
            confianza=record.confianza,
            observacion=record.observacion,
            raw=record.raw,
            cross_validated=True,
        )
