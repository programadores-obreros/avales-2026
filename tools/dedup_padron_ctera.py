#!/usr/bin/env python3
"""Deduplica ctera/consolidado/padron_ctera_2026.json.

Hallazgo (auditoría 2026-08-21, ver memoria del proyecto:
discovery/audit-ctera-consolidado-...): cada PDF de SUTEBA (uno por
distrito bonaerense) trae una sección "MESA N: <distrito> [SOLO VOTO
OBSERVADO]" que es una categoría LEGÍTIMA del padrón (no un error), pero
el consolidador original la trataba como una mesa más -> las personas que
figuran ahí Y en su mesa habitual quedaban con 2 registros.

Estrategia:
    1. Re-lee ctera/padronessuteba.zip SOLO para mapear, por archivo,
       qué número de mesa corresponde a la sección "[SOLO VOTO OBSERVADO]"
       (no vuelve a parsear filas de personas — liviano).
    2. Agrupa el consolidado por (dni, archivo_origen).
    3. Si un grupo de 2 tiene exactamente un registro en la mesa de voto
       observado y otro en su mesa real -> fusiona en 1 registro: se
       queda con los datos de la mesa REAL y agrega `voto_observado: true`.
    4. Duplicados EXACTOS (mismo dni+sindicato+provincia+mesa, en
       cualquier sindicato) -> colapsan a 1 (doble conteo puro).
    5. Todo lo demás (sin match de ninguna de las reglas de arriba,
       incluye los 246 casos de ADF con patrón distinto y los 2217
       cross-sindicato/provincia) -> se deja SIN TOCAR, reportado aparte
       para revisión manual.

No pisa el original: escribe ctera/consolidado/padron_ctera_2026_dedup.json
+ ctera/consolidado/reporte_dedup.json con los conteos de cada categoría.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CTERA_DIR = PROJECT_ROOT / "ctera"
ZIP_SUTEBA = CTERA_DIR / "padronessuteba.zip"
CONSOLIDADO_DIR = CTERA_DIR / "consolidado"
IN_JSON = CONSOLIDADO_DIR / "padron_ctera_2026.json"
OUT_JSON = CONSOLIDADO_DIR / "padron_ctera_2026_dedup.json"
OUT_REPORTE = CONSOLIDADO_DIR / "reporte_dedup.json"

MESA_SUTEBA_RE = re.compile(r"^MESA\s+(\d+):\s*(.+?)\s*$", re.MULTILINE)
VOTO_OBSERVADO_RE = re.compile(r"SOLO VOTO OBSERVADO", re.IGNORECASE)


# Sufijo pegado al nombre en algunos PDF de SUTE (confirmado con bounding
# boxes del PDF: es un objeto de texto SEPARADO, casi sin espacio, después
# del nombre — dato real de la fuente, no un artefacto de extracción, pero
# de significado desconocido). Auditoría 2026-08-22: 25 de 26 duplicados
# cross-archivo de SUTE diferían SOLO en este sufijo. Solo se sacan
# patrones inequívocamente seguros:
#   - "PD" literal (confirmado con 3 casos verificados contra el PDF)
#   - cualquier código con dígito (NINGÚN nombre real en español tiene
#     dígitos, cero riesgo de comerse parte de un nombre)
# Deliberadamente NO se sacan sufijos de 2 letras genéricos como "RE"
# sueltos — hay apellidos reales que terminan así (TORRE, AGUIRRE...);
# verificado que "PD" + dígito alcanza para resolver 25/26 sin esa regla.
SUFIJO_FUENTE_RE = re.compile(r"\s*(PD|[A-ZÑ]{0,2}\d+)$")


def nombre_comparable(nombre: str) -> str:
    """Clave de comparación para detectar 'misma persona, mismo DNI'.

    El `clean_name()` del consolidador original solo saca comas al inicio/fin
    del string, no las internas -> la MISMA persona queda con dos variantes
    ("APELLIDO Nombre" vs "APELLIDO, Nombre") según cómo la tipeó la fuente.
    Confirmado en 4/27 casos de ADF (2026-08-21). Solo se usa para comparar;
    el campo `apellido_nombre` guardado en el registro NO se toca.
    """
    limpio = re.sub(r"\s{2,}", " ", nombre.replace(",", " ")).strip().upper()
    return SUFIJO_FUENTE_RE.sub("", limpio).strip()


def pdf_to_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def build_voto_observado_map() -> dict[str, set[str]]:
    """archivo_origen -> {mesas que son "SOLO VOTO OBSERVADO" en ese PDF}."""
    mapa: dict[str, set[str]] = {}
    with tempfile.TemporaryDirectory(prefix="ctera_dedup_") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(ZIP_SUTEBA) as zf:
            for info in zf.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                    continue
                dest = tmp_path / "x.pdf"
                with zf.open(info) as src, open(dest, "wb") as out:
                    out.write(src.read())
                text = pdf_to_text(dest)
                mesas_observadas = set()
                for m in MESA_SUTEBA_RE.finditer(text):
                    mesa_num, resto = m.group(1), m.group(2)
                    if VOTO_OBSERVADO_RE.search(resto):
                        mesas_observadas.add(mesa_num)
                mapa[info.filename] = mesas_observadas
    return mapa


def run() -> None:
    print("Reconstruyendo mapa de mesas 'voto observado' desde los PDFs de SUTEBA...")
    voto_observado_map = build_voto_observado_map()
    total_archivos_con_vo = sum(1 for v in voto_observado_map.values() if v)
    print(f"  {total_archivos_con_vo} archivos con sección de voto observado detectada")

    print("Cargando consolidado...")
    with open(IN_JSON, encoding="utf-8") as f:
        records = json.load(f)
    print(f"  {len(records)} registros")

    # Validación cruzada para DNIs de 9 dígitos (nunca válidos en Argentina):
    # si el MISMO nombre normalizado aparece en otro registro del dataset con
    # un DNI de 8 dígitos que es EXACTAMENTE el prefijo del de 9 dígitos, hay
    # evidencia independiente de cuál es el DNI real -> se corrige. Sin ese
    # cruce no se adivina (probado en auditoría 2026-08-21: de 23 casos, solo
    # 1 tuvo match cruzado; generalizar "sacar el último dígito" a partir de
    # una sola muestra sería arriesgar corromper un DNI real). Se aplica ANTES
    # de agrupar -> si el DNI corregido coincide con el de otro registro del
    # mismo archivo, ambos caen en el mismo grupo y se fusionan normalmente
    # (en vez de quedar corregidos-pero-duplicados).
    dni8_por_nombre: dict[str, set[str]] = {}
    for r in records:
        if len(r["dni"]) == 8:
            dni8_por_nombre.setdefault(nombre_comparable(r["apellido_nombre"]), set()).add(r["dni"])

    n_dni_corregido = 0
    n_dni_sospechoso = 0
    for r in records:
        if len(r["dni"]) == 9:
            candidatos = dni8_por_nombre.get(nombre_comparable(r["apellido_nombre"]), set())
            prefijo = r["dni"][:8]
            if prefijo in candidatos:
                r["dni_original_9dig"] = r["dni"]
                r["dni"] = prefijo
                r["dni_corregido"] = True
                n_dni_corregido += 1
            else:
                r["dni_sospechoso"] = True
                n_dni_sospechoso += 1

    groups: dict[tuple, list[dict]] = {}
    for r in records:
        key = (r["dni"], r["archivo_origen"])
        groups.setdefault(key, []).append(r)

    out: list[dict] = []
    n_fusionados_voto_observado = 0
    n_colapsados_exactos = 0
    n_fusionados_mismo_nombre = 0
    n_sin_tocar_multi = 0
    grupos_sin_tocar_ejemplo: list[dict] = []

    def con_flags(r: dict, voto_observado: bool = False, mesas_duplicadas: list[str] | None = None) -> dict:
        r2 = dict(r)
        r2["voto_observado"] = voto_observado
        if mesas_duplicadas is not None:
            r2["mesas_duplicadas"] = mesas_duplicadas
        r2.setdefault("dni_sospechoso", False)
        r2.setdefault("dni_corregido", False)
        return r2

    for (dni, archivo), grupo in groups.items():
        if len(grupo) == 1:
            out.append(con_flags(grupo[0]))
            continue

        # duplicados EXACTOS (mismo sindicato+provincia+mesa) -> colapsar.
        # Si alguno de los miembros del grupo llegó acá por una corrección de
        # DNI (9->8 dígitos, ver arriba), preferirlo como base para no perder
        # la trazabilidad `dni_corregido`/`dni_original_9dig`.
        #
        # CRÍTICO (auditoría 2026-08-22): esto SOLO es seguro si además el
        # nombre coincide. Un mismo DNI+sindicato+provincia+mesa puede
        # corresponder a DOS PERSONAS DISTINTAS si el DNI fue mal
        # parseado/leído en la fuente original — caso confirmado: DNI
        # 22919333 en UEPC/Córdoba tenía a BULACIOS GERARDO MAXIMO
        # (FALLECIDO) y a STRATTA ARIELA como personas distintas; la versión
        # anterior de este código colapsaba por firma sola y perdía a
        # STRATTA sin dejar rastro. Ahora se exige también nombre igual;
        # si no coincide, cae a las reglas siguientes (y en el peor caso a
        # "sin tocar" para revisión manual) en vez de perder a alguien.
        firmas = {(r["sindicato"], r["provincia"], r["mesa"]) for r in grupo}
        nombres_firma = {nombre_comparable(r["apellido_nombre"]) for r in grupo}
        if len(firmas) == 1 and len(nombres_firma) == 1 and len(grupo) > 1:
            base = next((r for r in grupo if r.get("dni_corregido")), grupo[0])
            out.append(con_flags(base))
            n_colapsados_exactos += len(grupo) - 1
            continue

        if len(grupo) == 2:
            mesas_vo = voto_observado_map.get(archivo, set())
            a, b = grupo
            a_es_vo = a["mesa"] in mesas_vo
            b_es_vo = b["mesa"] in mesas_vo
            if a_es_vo != b_es_vo:  # exactamente uno de los dos es voto observado
                real = b if a_es_vo else a
                out.append(con_flags(real, voto_observado=True))
                n_fusionados_voto_observado += 1
                continue

        # mismo DNI + mismo nombre EXACTO (ya normalizado por el consolidador),
        # distinta mesa -> es la misma persona listada más de una vez en la
        # fuente (patrón visto en ADF y otros; sin marcador explícito como el
        # de "voto observado" de SUTEBA). Se fusiona quedándose con el primer
        # registro y preservando TODAS las mesas originales en
        # `mesas_duplicadas`, para no perder esa información.
        nombres = {nombre_comparable(r["apellido_nombre"]) for r in grupo}
        if len(nombres) == 1:
            mesas = [r["mesa"] for r in grupo]
            es_vo = any(r["mesa"] in voto_observado_map.get(archivo, set()) for r in grupo)
            # preferir como base la variante SIN coma (más prolija), si existe
            base = next((r for r in grupo if "," not in r["apellido_nombre"]), grupo[0])
            out.append(con_flags(base, voto_observado=es_vo, mesas_duplicadas=mesas))
            n_fusionados_mismo_nombre += len(grupo) - 1
            continue

        # no matchea ninguna regla de fusión conocida -> se deja sin tocar
        for r in grupo:
            out.append(con_flags(r))
        n_sin_tocar_multi += 1
        if len(grupos_sin_tocar_ejemplo) < 5:
            grupos_sin_tocar_ejemplo.append(
                {
                    "archivo_origen": archivo,
                    "sindicato": grupo[0]["sindicato"],
                    "mesas": [r["mesa"] for r in grupo],
                }
            )

    n_antes_pasada2 = len(out)

    # --- Segunda pasada: duplicados que cruzan archivo_origen dentro del
    # MISMO sindicato (auditoría 2026-08-22, deuda técnica documentada tras
    # el reimport a Firestore: la primera pasada agrupa por
    # (dni, archivo_origen), así que la MISMA persona listada en DOS
    # archivos-mesa distintos del mismo sindicato nunca se comparaba entre
    # sí — quedaba como 2 registros. Casos confirmados: AGMER, ATECH, SUTE
    # (~15 registros de 366k). Mismo criterio conservador que la primera
    # pasada: solo fusiona si el nombre normalizado coincide EXACTO; si no,
    # se deja como personas distintas para revisión manual.
    groups2: dict[tuple, list[dict]] = {}
    for r in out:
        groups2.setdefault((r["dni"], r["sindicato"]), []).append(r)

    out2: list[dict] = []
    n_fusionados_cross_archivo = 0
    n_sin_tocar_cross_archivo = 0
    grupos_cross_sin_tocar_ejemplo: list[dict] = []

    for (dni, sindicato), grupo in groups2.items():
        if len(grupo) == 1:
            out2.append(grupo[0])
            continue

        nombres = {nombre_comparable(r["apellido_nombre"]) for r in grupo}
        if len(nombres) == 1:
            mesas: list[str] = []
            archivos: list[str] = []
            for r in grupo:
                mesas.extend(r.get("mesas_duplicadas") or [r["mesa"]])
                archivos.append(r["archivo_origen"])
            base = next((r for r in grupo if "," not in r["apellido_nombre"]), grupo[0])
            r2 = dict(base)
            r2["mesas_duplicadas"] = mesas
            r2["archivos_duplicados"] = archivos
            out2.append(r2)
            n_fusionados_cross_archivo += len(grupo) - 1
            continue

        # nombres distintos con mismo dni+sindicato -> personas distintas
        # (mismo patrón que BULACIOS/STRATTA, ver primera pasada) -> sin tocar
        out2.extend(grupo)
        n_sin_tocar_cross_archivo += 1
        if len(grupos_cross_sin_tocar_ejemplo) < 5:
            grupos_cross_sin_tocar_ejemplo.append(
                {
                    "dni": dni,
                    "sindicato": sindicato,
                    "nombres": [r["apellido_nombre"] for r in grupo],
                    "archivos": [r["archivo_origen"] for r in grupo],
                }
            )

    out = out2
    print(f"\nSegunda pasada (cross-archivo, mismo sindicato): {n_antes_pasada2} -> {len(out)}")
    print(f"  - fusionados cross-archivo: {n_fusionados_cross_archivo}")
    print(f"  - grupos cross-archivo sin tocar: {n_sin_tocar_cross_archivo}")

    reporte = {
        "total_registros_entrada": len(records),
        "total_registros_salida": len(out),
        "registros_eliminados": len(records) - len(out),
        "fusionados_voto_observado_suteba": n_fusionados_voto_observado,
        "fusionados_mismo_nombre_exacto": n_fusionados_mismo_nombre,
        "colapsados_duplicado_exacto": n_colapsados_exactos,
        "grupos_multi_sin_tocar": n_sin_tocar_multi,
        "dni_corregido_por_match_cruzado": n_dni_corregido,
        "dni_sospechoso_9_digitos_sin_confirmar": n_dni_sospechoso,
        "fusionados_cross_archivo_mismo_sindicato": n_fusionados_cross_archivo,
        "grupos_cross_archivo_sin_tocar": n_sin_tocar_cross_archivo,
        "ejemplos_grupos_sin_tocar": grupos_sin_tocar_ejemplo,
        "ejemplos_grupos_cross_archivo_sin_tocar": grupos_cross_sin_tocar_ejemplo,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(OUT_REPORTE, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"Registros entrada:  {reporte['total_registros_entrada']}")
    print(f"Registros salida:   {reporte['total_registros_salida']}")
    print(f"Eliminados (dedup): {reporte['registros_eliminados']}")
    print(f"  - fusionados voto observado (SUTEBA): {n_fusionados_voto_observado}")
    print(f"  - fusionados mismo nombre exacto:     {n_fusionados_mismo_nombre}")
    print(f"  - colapsados duplicado exacto:        {n_colapsados_exactos}")
    print(f"Grupos multi SIN tocar (revisión manual): {n_sin_tocar_multi}")
    print(f"DNIs corregidos por match cruzado (9->8 dígitos): {n_dni_corregido}")
    print(f"DNIs sospechosos SIN confirmar (9 dígitos, sin tocar): {n_dni_sospechoso}")
    print(f"Fusionados cross-archivo (mismo sindicato, 2da pasada): {n_fusionados_cross_archivo}")
    print(f"Grupos cross-archivo SIN tocar (revisión manual): {n_sin_tocar_cross_archivo}")
    print(f"-> {OUT_JSON}")
    print(f"-> {OUT_REPORTE}")


if __name__ == "__main__":
    run()
