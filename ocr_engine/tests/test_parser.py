"""Parametrized tests for PadronParser — validates line parsing and page parsing."""

import pytest

from ocr_engine.parsing.parser import PadronParser


@pytest.fixture
def parser() -> PadronParser:
    return PadronParser("069")


@pytest.fixture
def parser_base() -> PadronParser:
    return PadronParser()


# ============================================================
# FULL MATCH — DNI + nombre + escuela + mesa
# ============================================================

class TestFullMatch:

    @pytest.mark.parametrize("input_line,doc,nombre,destino,mesa", [
        (
            "DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 1",
            "27241872", "VILLAFAÑE JORGE", "0-069-MT-0001", 1,
        ),
        (
            "DNI 14009185 PEREZ JUAN  0-069-MS-0042 5",
            "14009185", "PEREZ JUAN", "0-069-MS-0042", 5,
        ),
        (
            "DNI 32456789 GONZALEZ MARIA ANA  0-069-EE-0501 12",
            "32456789", "GONZALEZ MARIA ANA", "0-069-EE-0501", 12,
        ),
    ])
    def test_standard_escuela_code(self, parser, input_line, doc, nombre, destino, mesa):
        rec = parser.parse_line(input_line)
        assert rec is not None
        assert rec.documento == doc
        assert rec.nombre == nombre
        assert rec.destino == destino
        assert rec.mesa == mesa
        assert rec.tipo == "DNI"

    @pytest.mark.parametrize("input_line,doc,destino", [
        (
            "DNI 17257008 ZARATE SONIA BEATRIZ  JUBILADO/A 3",
            "17257008", "JUBILADO/A",
        ),
        (
            "DNI 12345678 GARCIA PEDRO  JUBILADA 7",
            "12345678", "JUBILADO/A",
        ),
    ])
    def test_jubilado(self, parser, input_line, doc, destino):
        rec = parser.parse_line(input_line)
        assert rec is not None
        assert rec.documento == doc
        assert rec.destino == destino
        assert rec.is_jubilado

    def test_ap_en_sede(self, parser):
        rec = parser.parse_line("DNI 22334455 LOPEZ MARTINEZ ANA  AP. EN SEDE 2")
        assert rec is not None
        assert rec.documento == "22334455"
        assert rec.destino == "AP. EN SEDE"
        assert rec.is_ap_en_sede


# ============================================================
# TIPO DOCUMENTO — LC, LE
# ============================================================

class TestTipoDocumento:

    def test_lc_tipo(self, parser):
        rec = parser.parse_line("LC 7654321 MARTINEZ ANA  0-069-PP-0012 1")
        assert rec is not None
        assert rec.tipo == "LC"
        assert rec.documento == "7654321"

    def test_le_tipo(self, parser):
        rec = parser.parse_line("LE 8765432 RODRIGUEZ CARLOS  0-069-DM-0003 4")
        assert rec is not None
        assert rec.tipo == "LE"
        assert rec.documento == "8765432"


# ============================================================
# RESCUE — mesa number garbled
# ============================================================

class TestRescueParsing:

    def test_garbled_mesa(self, parser):
        rec = parser.parse_line(
            "DNI 27241872 VILLAFAÑE JORGE 0-069-MT-0001", last_mesa=5
        )
        assert rec is not None
        assert rec.documento == "27241872"
        assert rec.mesa == 5  # Uses last_mesa fallback

    def test_jubilado_no_mesa(self, parser):
        rec = parser.parse_line(
            "DNI 17257008 ZARATE SONIA JUBILADO/A", last_mesa=3
        )
        assert rec is not None
        assert rec.destino == "JUBILADO/A"
        assert rec.mesa == 3


# ============================================================
# NULL / GARBAGE — should return None
# ============================================================

class TestNullCases:

    def test_empty_string(self, parser):
        assert parser.parse_line("") is None

    def test_whitespace(self, parser):
        assert parser.parse_line("   ") is None

    def test_short_line(self, parser):
        assert parser.parse_line("ABC DEF") is None

    def test_header_line(self, parser):
        # Header line gets matched by simple fallback (all uppercase >4 chars)
        # but with low confidence (0.4) — filtered at pipeline level
        rec = parser.parse_line("TIPO  DOCUMENTO  NOMBRE  ESCUELA")
        assert rec is None or rec.confianza < 0.5

    def test_pure_garbage(self, parser):
        assert parser.parse_line("|||---...===") is None


# ============================================================
# SANITIZER INTEGRATION — OCR artifacts cleaned before parsing
# ============================================================

class TestSanitizerIntegration:

    def test_d069_fixed_before_parse(self, parser):
        rec = parser.parse_line("DNI 14009185 PEREZ JUAN  D-069-MS-0042 1")
        assert rec is not None
        assert rec.destino == "0-069-MS-0042"

    def test_ms5_fixed_before_parse(self, parser):
        rec = parser.parse_line("DNI 14009185 PEREZ JUAN  0-069-MS5-0042 1")
        assert rec is not None
        assert rec.destino == "0-069-MS-0042"

    def test_dni_trailing_punct_fixed(self, parser):
        rec = parser.parse_line("DNI 14009185. PEREZ JUAN  0-069-MT-0001 1")
        assert rec is not None
        assert rec.documento == "14009185"


# ============================================================
# PARSE PAGE — full page text
# ============================================================

class TestParsePage:

    def test_simple_page(self, parser):
        text = """MESA: 5

DNI 27241872 VILLAFAÑE JORGE  0-069-MT-0001 5
DNI 14009185 PEREZ JUAN  0-069-MS-0042 5
DNI 17257008 ZARATE SONIA  JUBILADO/A 5
some garbage line
DNI 32456789 GONZALEZ ANA  0-069-EE-0501 5
"""
        records = parser.parse_page(text, page_num=1)
        assert len(records) == 4
        assert records[0].documento == "27241872"
        assert records[2].destino == "JUBILADO/A"

    def test_empty_page(self, parser):
        assert parser.parse_page("", page_num=1) == []

    def test_mesa_header_tracking(self, parser):
        text = """MESA: 3
DNI 27241872 VILLAFAÑE JORGE 0-069-MT-0001
DNI 14009185 PEREZ JUAN 0-069-MS-0042
"""
        records = parser.parse_page(text, page_num=1)
        assert len(records) >= 1
        # Mesa should be tracked from header
        assert records[0].mesa == 3


# ============================================================
# PARTIAL LINE DETECTION
# ============================================================

class TestPartialLine:

    def test_detects_partial(self, parser):
        assert parser.is_partial_line("DNI 12345678 garbled text")

    def test_not_partial(self, parser):
        assert not parser.is_partial_line("some random text")
        assert not parser.is_partial_line("MESA: 5")
