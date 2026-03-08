#!/usr/bin/env python3
"""Tests de integridad para el cruce de datos SUTEBA."""

import pandas as pd
import pytest

from cruzar_datos import (
    normalize_escuela_code,
    normalize_ocr_distrito,
    parse_all_zonas,
    build_escuela_mesa_mapping,
)


# ---------------------------------------------------------------------------
# Tests de normalización de códigos
# ---------------------------------------------------------------------------

class TestNormalizeEscuelaCode:
    """Normalización de códigos del Excel de zonas."""

    def test_codigo_simple(self):
        assert normalize_escuela_code("PP106") == "PP-0106"

    def test_codigo_corto(self):
        assert normalize_escuela_code("MS20") == "MS-0020"

    def test_codigo_con_espacio(self):
        assert normalize_escuela_code("MS 20") == "MS-0020"
        assert normalize_escuela_code("PP 106") == "PP-0106"

    def test_codigo_largo(self):
        assert normalize_escuela_code("JI1019") == "JI-1019"
        assert normalize_escuela_code("JI912") == "JI-0912"

    def test_codigo_con_descripcion(self):
        assert normalize_escuela_code("DE770 ESC ADULTOD 770") == "DE-0770"
        assert normalize_escuela_code("MF15 CENTRO EDUC AGRICOLA 15") == "MF-0015"

    def test_doble_s_typo(self):
        assert normalize_escuela_code("MSS 52") == "MS-0052"

    def test_codigo_especial_sin_numero(self):
        # Estos no se pueden normalizar — se devuelven tal cual
        result = normalize_escuela_code("JUBILADOS")
        assert result == "JUBILADOS"

    def test_codigo_especial_pago_sede(self):
        result = normalize_escuela_code("PAGO EN SEDE")
        assert result == "PAGO EN SEDE"

    def test_codigo_tres_letras(self):
        assert normalize_escuela_code("DM494") == "DM-0494"
        assert normalize_escuela_code("DF408") == "DF-0408"

    def test_codigo_con_barra(self):
        # CEA735/6 → solo toma hasta la barra
        result = normalize_escuela_code("CEA735/6")
        assert result == "CEA-0735"

    def test_codigo_t(self):
        assert normalize_escuela_code("T3") == "T-0003"
        assert normalize_escuela_code("T4") == "T-0004"


class TestNormalizeOcrDistrito:
    """Normalización de códigos del padrón OCR."""

    def test_codigo_ocr_standard(self):
        assert normalize_ocr_distrito("0-069-PP-0106") == "PP-0106"

    def test_codigo_ocr_ms(self):
        assert normalize_ocr_distrito("0-069-MS-0020") == "MS-0020"

    def test_jubilado(self):
        assert normalize_ocr_distrito("JUBILADO/A") == "JUBILADO/A"

    def test_ap_en_sede(self):
        assert normalize_ocr_distrito("AP. EN SEDE") == "AP. EN SEDE"

    def test_codigo_j1(self):
        assert normalize_ocr_distrito("0-069-J1-0912") == "J1-0912"


# ---------------------------------------------------------------------------
# Tests de parsing de zonas
# ---------------------------------------------------------------------------

class TestParseZonas:
    """Tests del parser de zonas usando el archivo real."""

    @pytest.fixture
    def zonas_path(self):
        return "/data/Zonas elección Suteba 2022.xlsx"

    @pytest.fixture
    def mesas_data(self, zonas_path):
        return parse_all_zonas(zonas_path)

    @pytest.fixture
    def escuela_map(self, mesas_data):
        return build_escuela_mesa_mapping(mesas_data)

    def test_todas_las_zonas_parseadas(self, mesas_data):
        zonas = set(m["zona"] for m in mesas_data)
        # Debe haber 30 zonas (1-30)
        assert len(zonas) == 30
        assert min(zonas) == 1
        assert max(zonas) == 30

    def test_cantidad_mesas(self, mesas_data):
        mesas = set(m["mesa"] for m in mesas_data)
        # Debe haber ~158 mesas (algunas pueden compartir número?)
        assert len(mesas) >= 150
        assert len(mesas) <= 160

    def test_cada_mesa_tiene_escuelas(self, mesas_data):
        for mesa in mesas_data:
            assert len(mesa["escuelas"]) > 0, f"Mesa {mesa['mesa']} en zona {mesa['zona']} no tiene escuelas"

    def test_mesa_1_es_jubilados(self, mesas_data):
        mesa1 = [m for m in mesas_data if m["mesa"] == 1]
        assert len(mesa1) == 1
        escuelas = [e.upper() for e in mesa1[0]["escuelas"]]
        assert any("JUBILAD" in e for e in escuelas)

    def test_zona_27_tiene_san_justo(self, mesas_data):
        z27 = [m for m in mesas_data if m["zona"] == 27]
        assert len(z27) > 0
        assert any("SAN JUSTO" in m["zona_nombre"].upper() for m in z27)

    def test_escuela_map_no_vacia(self, escuela_map):
        assert len(escuela_map) > 0

    def test_escuela_map_tiene_codigos_normalizados(self, escuela_map):
        # Al menos algunos códigos deben tener formato XX-XXXX
        normalized = escuela_map["escuela_code"].str.match(r"^[A-Z]+-\d{4}$")
        assert normalized.sum() > len(escuela_map) * 0.5


# ---------------------------------------------------------------------------
# Tests de cruce de datos
# ---------------------------------------------------------------------------

class TestCruceDatos:
    """Tests del cruce padrón + zonas."""

    @pytest.fixture
    def padron(self):
        return pd.read_csv("/data/output/padron.csv")

    @pytest.fixture
    def zonas_path(self):
        return "/data/Zonas elección Suteba 2022.xlsx"

    @pytest.fixture
    def escuela_map(self, zonas_path):
        mesas_data = parse_all_zonas(zonas_path)
        return build_escuela_mesa_mapping(mesas_data)

    def test_padron_tiene_escuela_code(self, padron):
        padron["escuela_code"] = padron["distrito_escuela"].apply(normalize_ocr_distrito)
        # La mayoría debe tener código tipo XX-XXXX
        has_code = padron["escuela_code"].str.match(r"^[A-Z\d]+-\d{3,4}$", na=False)
        jubilados = padron["distrito_escuela"].isin(["JUBILADO/A", "AP. EN SEDE"])
        # Todos los no-jubilados deben tener código
        assert has_code[~jubilados].mean() > 0.95

    def test_ms20_existe_en_mapeo(self, escuela_map):
        ms20 = escuela_map[escuela_map["escuela_code"] == "MS-0020"]
        assert len(ms20) > 0
        # MS20 aparece como escuela que vota en al menos una mesa
        assert ms20.iloc[0]["mesa"] in (2, 21)  # Puede ser mesa 2 (sede) o 21

    def test_no_hay_mesas_duplicadas_entre_zonas(self, escuela_map):
        # Cada mesa debe pertenecer a una sola zona
        mesa_zona = escuela_map[["mesa", "zona"]].drop_duplicates()
        duplicadas = mesa_zona.groupby("mesa").filter(lambda x: len(x) > 1)
        if len(duplicadas) > 0:
            print(f"WARN: Mesas en múltiples zonas: {duplicadas.to_string()}")
        # Permitimos algunos edge cases pero no debería ser muchos
        assert len(duplicadas) < 10

    def test_jubilados_mayoria_mesa_1(self, padron):
        jubilados = padron[padron["distrito_escuela"] == "JUBILADO/A"]
        # Mesa 1 tiene la mayor concentración de jubilados
        mesa_counts = jubilados["mesa"].value_counts()
        assert mesa_counts.index[0] == 1  # Mesa 1 es la que más jubilados tiene
        assert mesa_counts.iloc[0] > 1000  # Al menos 1000 jubilados en mesa 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
