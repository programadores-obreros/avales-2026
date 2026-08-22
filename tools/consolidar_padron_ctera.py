#!/usr/bin/env python3
"""Consolida los padrones de CTERA 2026 (18 sindicatos) en un único JSON normalizado.

Elecciones nacionales CTERA, 2 de septiembre de 2026. Fuente: rama `ctera`.

Fuentes:
    ctera/Padron definitivo elecciones CTERA 2026-...zip
        -> 18 carpetas por sindicato (SUTEBA incompleta ahí, se ignora — ver nota)
    ctera/padronessuteba.zip
        -> fuente ÚNICA y completa de SUTEBA (verificado: contiene entero a
           padrones.zip y a la subcarpeta SUTEBA/ del zip grande — son
           subconjuntos redundantes, no datos nuevos)

Estrategia de parsing (ver docs/ o memoria del proyecto para el detalle):
    Hay 4 familias de formato de PDF (iText/SUTEBA, ReportLab/mayoría,
    Acrobat Distiller/ATECA, Excel/AMSAFE+ADEP) y dentro de "ReportLab" cada
    sindicato define sus propias columnas. En vez de un parser rígido por
    columna para cada uno, extraemos de forma position-agnostic:
        DNI            -> primer token de 6 a 9 dígitos (con puntos opcionales)
        apellido_nombre -> primer bloque de texto después del DNI, cortado en
                            el primer salto de 3+ espacios (separador de
                            columna típico de `pdftotext -layout`)
        detalle         -> el resto de la fila (escuela/mesa/departamento/etc,
                            sin parsear más) — así NUNCA se pierde información,
                            en el peor caso un apellido compuesto con espaciado
                            raro cae en `detalle` en vez de `apellido_nombre`.
    Validación: cada mesa declara "Total de electores/afiliados" en su header.
    Se compara contra las filas parseadas y se reporta cualquier discrepancia
    — no se asume que el parser funcionó, se verifica mesa por mesa.

Uso:
    python3 tools/consolidar_padron_ctera.py [--muestra]

    --muestra   sólo procesa 1 archivo por sindicato (para validar el parser
                rápido, sin extraer ni parsear los ~2000 PDFs completos)

Salida:
    ctera/consolidado/padron_ctera_2026.json       (records normalizados)
    ctera/consolidado/reporte_consolidacion.json   (conteos + discrepancias)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CTERA_DIR = PROJECT_ROOT / "ctera"
ZIP_GRANDE = CTERA_DIR / "Padron definitivo elecciones CTERA 2026-20260821T235158Z-1-001.zip"
ZIP_SUTEBA = CTERA_DIR / "padronessuteba.zip"
OUT_DIR = CTERA_DIR / "consolidado"

# Sindicato -> provincia. Verificado 2026-08-21 (ver memoria del proyecto:
# discovery/ctera-2026-... y decision/rama-ctera-...). Tucumán tiene DOS
# entidades de base (ATEP = nivel inicial/primario, APEMYS = medio/superior).
# Falta Tierra del Fuego (SUTEF) — no está en ninguno de los 3 zips fuente.
SINDICATO_PROVINCIA = {
    "SUTEBA": "Buenos Aires",
    "UTE": "Ciudad Autónoma de Buenos Aires",
    "UEPC": "Córdoba",
    "AGMER": "Entre Ríos",
    "AMSAFE": "Santa Fe",
    "ATEN": "Neuquén",
    "SUTE": "Mendoza",
    "ATECH": "Chubut",
    "ATECA": "Catamarca",
    "UNTER": "Río Negro",
    "ATEP": "Tucumán",
    "APEMYS": "Tucumán",
    "UDAP": "San Juan",
    "UDPM": "Misiones",
    "ADP": "Salta",
    "ADEP": "Jujuy",
    "SUTECO": "Corrientes",
    "CISADEMS": "Santiago del Estero",
    # single-file, sueltos en la raíz del zip (no en carpeta propia) — se me
    # habían pasado en el primer análisis por carpeta
    "ASDE": "San Luis",
    "AMP": "La Rioja",
    "ADF": "Formosa",
    "UTELPA": "La Pampa",
    "UTRE": "Chaco",
    "ADOSAC": "Santa Cruz",
}

# Sindicatos donde la fila trae "Apellido y Nombre" ANTES del DNI (al revés
# que el resto). Verificado leyendo el header de cada uno.
NOMBRE_ANTES_DE_DNI = {"ADF", "AMP", "UTRE", "ADOSAC", "AMSAFE"}

# La mesa viene como columna de tabla (no como texto "MESA N") -> fallback
# heurístico en parse_generic_pdf (ver ahí). Auditoría 2026-08-22: antes de
# esto, el 100% de UTELPA/UTRE quedaba con mesa="?".
MESA_EN_COLUMNA_DETALLE = {"UTELPA", "UTRE"}

DNI_RE = re.compile(r"\b(\d{1,3}(?:\.\d{3}){1,2}|\d{6,9})\b")
TOTAL_RE = re.compile(
    r"Total de (?:electores|afiliados(?:/as)? habilitados(?:/as)?(?: para votar)?)"
    r"[^\d]{0,20}(\d+)",
    re.IGNORECASE,
)
TOTAL_RE_ALT = re.compile(r"(\d+)\s*electores\b", re.IGNORECASE)
# captura un sufijo de letra pegado al número (ADOSAC desdobla mesas en
# "1A"/"1B" — sin esto, ambas colapsaban al mismo "1" y se perdían 2 mesas
# reales; auditoría 2026-08-22)
MESA_RE = re.compile(r"MESA\s*[:\-–—]?\s*N?[°ºo]?\.?\s*(\d+[A-Za-z]?)", re.IGNORECASE)
MESA_FILENAME_RE = re.compile(r"Mesa[_\s]*0*(\d+)", re.IGNORECASE)
JUB_RE = re.compile(r"\bJUB\b|JUBILAD", re.IGNORECASE)


@dataclass
class Record:
    dni: str
    apellido_nombre: str
    sindicato: str
    provincia: str
    mesa: str
    jubilado: bool
    detalle: str
    formato_origen: str
    archivo_origen: str


def pdf_to_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def clean_name(raw: str) -> str:
    raw = raw.strip().strip(",")
    raw = re.sub(r"\s{2,}", " ", raw)
    return raw


def extract_dni(fragment: str) -> str | None:
    m = DNI_RE.search(fragment)
    if not m:
        return None
    digits = m.group(1).replace(".", "")
    if 6 <= len(digits) <= 9:
        return digits
    return None


ORDER_PREFIX_RE = re.compile(r"^\s*\d{1,4}\s*[\)\.]?\s+")
TRAILING_DOC_LABEL_RE = re.compile(r"\s+(?:DNI|D\.N\.I\.?|LC|LE|CI|OTRO)\s*-?\s*$", re.IGNORECASE)


def parse_generic_row(line: str, nombre_antes: bool = False) -> tuple[str, str, str] | None:
    """DNI, nombre, detalle — position-agnostic, no pierde texto.

    nombre_antes=True: la fila trae "Apellido y Nombre" ANTES del DNI
    (ADF/AMP/UTRE/ADOSAC), no después como en el resto.
    """
    m = DNI_RE.search(line)
    if not m:
        return None
    digits = m.group(1).replace(".", "")
    if not (6 <= len(digits) <= 9):
        return None

    if nombre_antes:
        before = line[: m.start()]
        before = ORDER_PREFIX_RE.sub("", before, count=1)
        before = TRAILING_DOC_LABEL_RE.sub("", before)
        nombre = clean_name(before)
        if not nombre:
            return None
        rest = line[m.end():]
        parts = [p for p in re.split(r"\s{3,}", rest.strip()) if p.strip()]
        detalle = " | ".join(clean_name(p) for p in parts)
        return digits, nombre, detalle

    rest = line[m.end():]
    parts = re.split(r"\s{3,}", rest.strip())
    parts = [p for p in parts if p.strip()]
    if not parts:
        return None
    nombre = clean_name(parts[0])
    detalle = " | ".join(clean_name(p) for p in parts[1:])
    return digits, nombre, detalle


def parse_generic_pdf(text: str, sindicato: str, archivo: str, formato: str) -> tuple[list[Record], int | None]:
    provincia = SINDICATO_PROVINCIA[sindicato]
    nombre_antes = sindicato in NOMBRE_ANTES_DE_DNI
    records: list[Record] = []

    total_m = TOTAL_RE.search(text) or TOTAL_RE_ALT.search(text)
    total_declarado = int(total_m.group(1)) if total_m else None

    fn_m = MESA_FILENAME_RE.search(archivo)
    if fn_m:
        mesa_default = fn_m.group(1)
    elif re.search(r"MESA\s+[UÚ]NICA", text[:400], re.IGNORECASE):
        mesa_default = "Única"  # ASDE: literalmente no hay más de una mesa
    else:
        mesa_default = "?"

    # Marcadores "MESA N" a lo largo de TODO el archivo (algunos, como AMP,
    # traen varias mesas en un mismo PDF de 45 páginas) — se usa el más
    # cercano ANTES de cada fila, no solo el primero del archivo.
    marcadores = [(m.start(), m.group(1)) for m in MESA_RE.finditer(text)]
    mesa_actual = marcadores[0][1] if marcadores else mesa_default
    marcador_idx = 0

    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\n").rstrip()
        line_offset = offset
        offset += len(raw_line)
        if not line.strip():
            continue

        while marcador_idx < len(marcadores) and marcadores[marcador_idx][0] <= line_offset:
            mesa_actual = marcadores[marcador_idx][1]
            marcador_idx += 1

        parsed = parse_generic_row(line, nombre_antes=nombre_antes)
        if parsed is None:
            continue
        dni, nombre, detalle = parsed
        if not nombre or nombre.isdigit():
            # línea que matcheó un número largo pero no tiene nombre al lado
            # (p.ej. encabezados con "N° 2026" o similar) -> descartar
            continue
        row_mesa_m = MESA_RE.search(detalle)
        row_mesa = row_mesa_m.group(1) if row_mesa_m else mesa_actual
        if row_mesa == "?" and sindicato in MESA_EN_COLUMNA_DETALLE:
            # UTELPA/UTRE traen la mesa como columna de tabla, no como texto
            # "MESA N" — no hay forma de detectarla con MESA_RE. Si hay
            # exactamente un fragmento numérico puro en `detalle`, es la
            # mesa (auditoría 2026-08-22: sin esto, el 100% de estos 2
            # sindicatos quedaba en mesa="?").
            candidatos = [p for p in detalle.split(" | ") if p.isdigit()]
            if len(candidatos) == 1:
                row_mesa = candidatos[0]
        records.append(
            Record(
                dni=dni,
                apellido_nombre=nombre,
                sindicato=sindicato,
                provincia=provincia,
                mesa=row_mesa,
                jubilado=bool(JUB_RE.search(detalle) or JUB_RE.search(nombre)),
                detalle=detalle,
                formato_origen=formato,
                archivo_origen=archivo,
            )
        )
    return records, total_declarado


MESA_SUTEBA_RE = re.compile(
    r"^MESA\s+(\d+):\s*(.+?)(?:\s*\[.*\])?\s*$", re.MULTILINE
)


TOTAL_MESA_SUTEBA_RE = re.compile(r"TOTAL MESA:\s*(\d+)", re.IGNORECASE)


def parse_suteba_pdf(text: str, archivo: str) -> tuple[list[Record], list[dict]]:
    """Family iText: un PDF por partido, con varias secciones `MESA N: ...`.

    Cada mesa SÍ declara su propio total ("TOTAL MESA: N", una vez por mesa,
    al final de su bloque) — el comentario anterior de este código decía que
    SUTEBA no declaraba total; era falso, la auditoría del 2026-08-22 lo
    encontró y acá se usa para validar mesa por mesa, igual que el resto de
    los sindicatos.
    """
    records: list[Record] = []
    discrepancias: list[dict] = []
    sections = list(MESA_SUTEBA_RE.finditer(text))
    if not sections:
        return [], []

    # El header "MESA N: ..." se REPITE en cada página como encabezado de
    # página cuando una mesa ocupa varias páginas — no es una sección nueva.
    # Fusionar ocurrencias consecutivas con el MISMO número de mesa en un
    # solo bloque lógico (si no, el total declarado — que aparece una sola
    # vez, al final de la mesa completa — se compara contra un fragmento de
    # una sola página y da falsos "faltan cientos de personas").
    bloques: list[tuple[str, int, int]] = []  # (mesa_num, start, end)
    for i, sec in enumerate(sections):
        mesa_num = sec.group(1)
        start = sec.end()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        if bloques and bloques[-1][0] == mesa_num:
            bloques[-1] = (mesa_num, bloques[-1][1], end)
        else:
            bloques.append((mesa_num, start, end))

    for mesa_num, start, end in bloques:
        block = text[start:end]
        n_antes = len(records)
        for raw_line in block.splitlines():
            line = raw_line.rstrip()
            # Acepta DNI y también LC/LE/CI (Libreta Cívica/Enrolamiento,
            # Cédula de Identidad) — mayormente jubilados/as documentados con
            # esos tipos. Filtrar solo por "DNI" descartaba ~3.400 personas
            # reales en silencio (auditoría 2026-08-22, ver memoria).
            if not re.match(r"^\s*(DNI|LC|LE|CI|OTRO)\b", line, re.IGNORECASE):
                continue
            parsed = parse_generic_row(line)
            if parsed is None:
                continue
            dni, nombre, detalle = parsed
            records.append(
                Record(
                    dni=dni,
                    apellido_nombre=nombre,
                    sindicato="SUTEBA",
                    provincia="Buenos Aires",
                    mesa=mesa_num,
                    jubilado=bool(JUB_RE.search(detalle)),
                    detalle=detalle,
                    formato_origen="iText",
                    archivo_origen=archivo,
                )
            )
        total_m = TOTAL_MESA_SUTEBA_RE.search(block)
        if total_m:
            declarado = int(total_m.group(1))
            parseado = len(records) - n_antes
            if declarado != parseado:
                discrepancias.append(
                    {
                        "archivo": archivo,
                        "sindicato": "SUTEBA",
                        "mesa": mesa_num,
                        "total_declarado": declarado,
                        "total_parseado": parseado,
                    }
                )
    return records, discrepancias


def guess_formato(text: str) -> str:
    if "PADRON ALFABETICO" in text[:200].upper():
        return "iText"
    return "ReportLab_o_similar"


def iter_zip_pdfs(zip_path: Path, skip_prefix: str | None = None):
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                continue
            if skip_prefix and skip_prefix in info.filename:
                continue
            yield zf, info


def sindicato_from_path(name: str) -> str | None:
    for sind in SINDICATO_PROVINCIA:
        if f"/{sind}/" in name:
            return sind
    # archivos sueltos en la raíz del zip, ej. ".../ASDE.pdf" (sin carpeta)
    stem = Path(name).stem.upper()
    if stem in SINDICATO_PROVINCIA:
        return stem
    return None


def run(muestra: bool) -> None:
    all_records: list[Record] = []
    reporte: dict = {"por_sindicato": {}, "discrepancias": [], "sin_sindicato": []}
    vistos_por_sindicato: dict[str, int] = {}

    with tempfile.TemporaryDirectory(prefix="ctera_pdf_") as tmp:
        tmp_path = Path(tmp)

        # --- 17 sindicatos del zip grande (SUTEBA se ignora acá) ---
        for zf, info in iter_zip_pdfs(ZIP_GRANDE, skip_prefix="/SUTEBA/"):
            sind = sindicato_from_path(info.filename)
            if sind is None:
                reporte["sin_sindicato"].append(info.filename)
                continue
            if muestra and vistos_por_sindicato.get(sind, 0) >= 1:
                continue
            vistos_por_sindicato[sind] = vistos_por_sindicato.get(sind, 0) + 1

            dest = tmp_path / "x.pdf"
            with zf.open(info) as src, open(dest, "wb") as out:
                out.write(src.read())
            text = pdf_to_text(dest)
            if not text.strip():
                reporte["discrepancias"].append(
                    {"archivo": info.filename, "motivo": "pdftotext vacío o falló"}
                )
                continue
            formato = guess_formato(text)
            records, total_declarado = parse_generic_pdf(text, sind, info.filename, formato)
            all_records.extend(records)
            if total_declarado is not None and total_declarado != len(records):
                reporte["discrepancias"].append(
                    {
                        "archivo": info.filename,
                        "sindicato": sind,
                        "total_declarado": total_declarado,
                        "total_parseado": len(records),
                    }
                )

        # --- SUTEBA: única fuente = padronessuteba.zip ---
        count_suteba = 0
        for zf, info in iter_zip_pdfs(ZIP_SUTEBA):
            if muestra and count_suteba >= 1:
                continue
            count_suteba += 1
            dest = tmp_path / "y.pdf"
            with zf.open(info) as src, open(dest, "wb") as out:
                out.write(src.read())
            text = pdf_to_text(dest)
            if not text.strip():
                reporte["discrepancias"].append(
                    {"archivo": info.filename, "motivo": "pdftotext vacío o falló"}
                )
                continue
            records, discrepancias_mesa = parse_suteba_pdf(text, info.filename)
            if not records:
                reporte["discrepancias"].append(
                    {"archivo": info.filename, "sindicato": "SUTEBA", "motivo": "0 filas parseadas"}
                )
            reporte["discrepancias"].extend(discrepancias_mesa)
            all_records.extend(records)

    for r in all_records:
        reporte["por_sindicato"][r.sindicato] = reporte["por_sindicato"].get(r.sindicato, 0) + 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "padron_ctera_2026.json"
    out_reporte = OUT_DIR / "reporte_consolidacion.json"

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump([r.__dict__ for r in all_records], f, ensure_ascii=False, indent=2)

    reporte["total_registros"] = len(all_records)
    with open(out_reporte, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"Registros totales: {len(all_records)}")
    print("Por sindicato:")
    for sind, n in sorted(reporte["por_sindicato"].items(), key=lambda kv: -kv[1]):
        print(f"  {sind:10s} {n}")
    print(f"Discrepancias/errores: {len(reporte['discrepancias'])}")
    print(f"Sin sindicato detectado: {len(reporte['sin_sindicato'])}")
    print(f"-> {out_json}")
    print(f"-> {out_reporte}")


if __name__ == "__main__":
    run(muestra="--muestra" in sys.argv)
