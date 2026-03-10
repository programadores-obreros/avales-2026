"""Tests for CrossValidator — merging results from multiple engines."""

import pytest

from ocr_engine.models import PadronRecord
from ocr_engine.validator import CrossValidator


@pytest.fixture
def validator():
    return CrossValidator()


class TestCrossValidator:

    def test_single_engine_passthrough(self, validator):
        records = [
            PadronRecord(documento="12345678", nombre="PEREZ JUAN", destino="0-069-MS-0042"),
            PadronRecord(documento="87654321", nombre="GARCIA ANA", destino="JUBILADO/A"),
        ]
        merged = validator.validate({"tesseract": records})
        assert len(merged) == 2
        assert all(r.cross_validated for r in merged)

    def test_two_engines_agreement(self, validator):
        """Both engines agree on everything."""
        records_a = [
            PadronRecord(documento="12345678", nombre="PEREZ JUAN",
                        destino="0-069-MS-0042", confianza=0.8),
        ]
        records_b = [
            PadronRecord(documento="12345678", nombre="PEREZ JUAN",
                        destino="0-069-MS-0042", confianza=0.7),
        ]
        merged = validator.validate({"tesseract": records_a, "paddle": records_b})
        assert len(merged) == 1
        assert merged[0].documento == "12345678"
        assert merged[0].nombre == "PEREZ JUAN"
        assert merged[0].cross_validated

    def test_two_engines_disagreement_nombre(self, validator):
        """Engines disagree on nombre — highest confidence wins."""
        records_a = [
            PadronRecord(documento="12345678", nombre="PEREZ JIAN",
                        destino="0-069-MS-0042", confianza=0.5),
        ]
        records_b = [
            PadronRecord(documento="12345678", nombre="PEREZ JUAN",
                        destino="0-069-MS-0042", confianza=0.9),
        ]
        merged = validator.validate({"tesseract": records_a, "paddle": records_b})
        assert len(merged) == 1
        assert merged[0].nombre == "PEREZ JUAN"  # Higher confidence

    def test_two_engines_disagreement_destino(self, validator):
        """Engines disagree on destino — highest confidence wins."""
        records_a = [
            PadronRecord(documento="12345678", nombre="PEREZ JUAN",
                        destino="0-069-MS-0042", confianza=0.9),
        ]
        records_b = [
            PadronRecord(documento="12345678", nombre="PEREZ JUAN",
                        destino="0-069-MS-0043", confianza=0.5),
        ]
        merged = validator.validate({"tesseract": records_a, "paddle": records_b})
        assert len(merged) == 1
        assert merged[0].destino == "0-069-MS-0042"

    def test_disjoint_records(self, validator):
        """Engines found different records (different DNIs)."""
        records_a = [
            PadronRecord(documento="12345678", nombre="PEREZ", confianza=0.8),
        ]
        records_b = [
            PadronRecord(documento="87654321", nombre="GARCIA", confianza=0.7),
        ]
        merged = validator.validate({"tesseract": records_a, "paddle": records_b})
        assert len(merged) == 2
        docs = {r.documento for r in merged}
        assert "12345678" in docs
        assert "87654321" in docs

    def test_empty_results(self, validator):
        assert validator.validate({}) == []

    def test_confidence_averaging(self, validator):
        """Merged record confidence is average of inputs."""
        records_a = [
            PadronRecord(documento="12345678", confianza=0.8),
        ]
        records_b = [
            PadronRecord(documento="12345678", confianza=0.6),
        ]
        merged = validator.validate({"a": records_a, "b": records_b})
        assert len(merged) == 1
        assert merged[0].confianza == pytest.approx(0.7)

    def test_three_engines_majority_vote(self, validator):
        """Three engines — majority vote on tipo."""
        records_a = [PadronRecord(documento="12345678", tipo="DNI", confianza=0.7)]
        records_b = [PadronRecord(documento="12345678", tipo="LC", confianza=0.7)]
        records_c = [PadronRecord(documento="12345678", tipo="DNI", confianza=0.7)]
        merged = validator.validate({"a": records_a, "b": records_b, "c": records_c})
        assert len(merged) == 1
        assert merged[0].tipo == "DNI"  # 2 vs 1
