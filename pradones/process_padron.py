#!/usr/bin/env python3
"""
Procesador de Padrón Electoral SUTEBA
Extrae datos tabulares de PDFs escaneados usando OCR (Tesseract).

Uso:
    python process_padron.py --input padron_oficial.pdf --output ./output
    python process_padron.py -i padron_oficial.pdf -o ./output --pages 1-5
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Regex patterns — ordered from most specific to most flexible.
# Each captures: (TIPO, DOCUMENTO, NOMBRE, DISTRITO_ESCUELA, MESA)
#
# NOTE: All patterns end with `[\s\S]*$` to tolerate OCR garbage after the
# mesa number (scanner edge noise produces stray chars like |, >, ', etc.)
# ---------------------------------------------------------------------------
_TRAIL = r"[\s\S]*$"  # Absorbs any trailing OCR garbage

PATTERNS = [
    # --- Establishment code format: 0-069-MS-0042, 0-069-EE-0501, etc. ---
    # This is the most common format for non-jubilados (active teachers)
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+([\d]-[\d]{{2,3}}-[A-Z]{{2}}-[\d]{{3,4}})\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Establishment code with OCR variations (O instead of 0, etc.)
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+([O\d]-[O\d]{{2,3}}-[A-Z\d]{{2}}-[O\d]{{3,4}})\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # --- JUBILADO/A (with OCR variations) ---
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}(JUBILAD\S*/?\s*A)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # AP. EN SEDE (with OCR variations)
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}(AP\.?\s*EN\s*SEDE)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # TITULAR / SUPLENTE (posible en otros padrones)
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}(TITULAR|SUPLENTE)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Fallback: any uppercase text block (3+ chars) before a trailing number
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s{{2,}}([A-Z][A-Z\s./]{{2,}}?)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Last resort: single-space separation for known distrito values
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+(JUBILAD\S*/?\s*A|AP\.?\s*EN\s*SEDE)\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
    # Ultra-fallback: establishment code with single space separator
    re.compile(
        rf"^(DNI|L[CE])\.?\s+(\d{{4,9}})\.?\s+(.+?)\s+([\dO]-[\dO]{{2,3}}-[A-Z\d]{{2}}-[\dO]{{3,4}})\s+(\d{{1,4}}){_TRAIL}",
        re.IGNORECASE,
    ),
]

# Pattern to detect MESA section header
MESA_HEADER = re.compile(r"MESA[:\s]+(\d+)[:\s]*(.*)", re.IGNORECASE)

# Pattern to detect lines that START like data but failed to parse
PARTIAL_LINE = re.compile(r"^(DNI|L[CE])\s+\d", re.IGNORECASE)

# Rescue pattern: when OCR mangles the mesa number, extract what we can
# and use context (last known mesa) to fill the gap
RESCUE_PATTERN = re.compile(
    r"^(DNI|L[CE])\.?\s+(\d{4,9})\.?\s+(.+?)\s+(JUBILAD\S*/?\s*\S*|AP\.?\s*EN\s*SEDE|[\dO]-[\dO]{2,3}-[A-Z\d]{2}-[\dO]{3,4})",
    re.IGNORECASE,
)


def sanitize_line(line: str) -> str:
    """Pre-process a line to fix common OCR artifacts in establishment codes.

    Fixes applied (only to the code portion, not the name):
    - Remove stray dots/commas/quotes next to DNI number: 'DNI 14009185.' → 'DNI 14009185'
    - Fix J|, J!, J1, )1, .J1, ,J1 → J1 in codes
    - Fix £E, A£ → EE, AE
    - Fix T.J → TJ, EL. → EL
    - Fix doubled chars: MS5 → MS, 8B5 → BS, A4A → AA, D0F → DF, D0M → DM, S5C → SC
    - Fix 0-0692- → 0-069-
    - Fix D-069 → 0-069
    - Fix space in code: '0-069- MS' → '0-069-MS', '0-069-MT -' → '0-069-MT-'
    - Fix 0-069.MS → 0-069-MS
    """
    s = line.strip()
    if not s:
        return s

    # Fix DNI number with trailing punctuation: 'DNI 14009185.' → 'DNI 14009185'
    s = re.sub(r"^((?:DNI|L[CE])\s+\d{4,9})[.,;:\"'_]+", r"\1", s)

    # Fix extra digit in 'DNI 2 14819326' → 'DNI 14819326'
    s = re.sub(r"^((?:DNI|L[CE])\s+)\d\s+(\d{4,9})", r"\1\2", s)

    # Fix extra chars appended to DNI number: '228690982' (9 digits) or '21548468B_'
    s = re.sub(r"^((?:DNI|L[CE])\s+\d{7,8})[A-Z_]+\s", r"\1 ", s)

    # --- Fix establishment code OCR errors ---
    # Fix D-069 → 0-069
    s = re.sub(r"D-069-", "0-069-", s)

    # Fix 0-0692- → 0-069-
    s = re.sub(r"0-0692-", "0-069-", s)

    # Fix 0-089 → 0-069 (common OCR: 6→8)
    # NOTE: keeping 0-089 as valid since it appeared in original data
    # Only fix if clearly wrong patterns

    # Fix space inside codes: '0-069- MS' → '0-069-MS', 'MT -0004' → 'MT-0004'
    s = re.sub(r"(0-069-)\s+", r"\1", s)
    s = re.sub(r"(\b[A-Z]{2})\s+-(\d{4})", r"\1-\2", s)

    # Fix dot/comma before code part: '.J1' → 'J1', ',J1' → 'J1', ',I-' → 'J1-'
    s = re.sub(r"0-069-[.,](J[1I])", r"0-069-\1", s)
    s = re.sub(r"0-069-[.,](\d)", r"0-069-J1-\1" if False else r"0-069-\1", s)

    # Fix J| → J1, J! → J1, )1 → J1, ,1 → J1 in codes
    s = re.sub(r"0-069-J[|!]", "0-069-J1", s)
    s = re.sub(r"0-069-\)1", "0-069-J1", s)
    s = re.sub(r"0-069-[.,;]1-", "0-069-J1-", s)
    s = re.sub(r"0-069-[.,;]I-", "0-069-JI-", s)

    # Fix .J1 → J1
    s = re.sub(r"0-069-\.J", "0-069-J", s)
    s = re.sub(r"0-069-\.1-", "0-069-J1-", s)

    # Fix £E → EE, E£ → EE, A£ → AE
    s = s.replace("£E", "EE").replace("E£", "EE").replace("A£", "AE")

    # Fix EL. → EL
    s = re.sub(r"EL\.-", "EL-", s)

    # Fix T.J → TJ
    s = re.sub(r"T\.J", "TJ", s)

    # Fix doubled/extra chars in 2-letter code: MS5→MS, 8B5→BS, A4A→AA,
    # D0F→DF, D0M→DM, S5C→SC, 8BS→BS, 85S→BS, 0DM→DM, etc.
    s = re.sub(r"0-069-MS5-", "0-069-MS-", s)
    s = re.sub(r"0-069-M3S-", "0-069-MS-", s)
    s = re.sub(r"0-069-8B5-", "0-069-BS-", s)
    s = re.sub(r"0-069-8BS-", "0-069-BS-", s)
    s = re.sub(r"0-069-85S-", "0-069-BS-", s)
    s = re.sub(r"0-069-A4A-", "0-069-AA-", s)
    s = re.sub(r"0-069-D0F-", "0-069-DF-", s)
    s = re.sub(r"0-069-D0M-", "0-069-DM-", s)
    s = re.sub(r"0-069-0DM-", "0-069-DM-", s)
    s = re.sub(r"0-069-S5C-", "0-069-SC-", s)
    s = re.sub(r"0-069-0F-", "0-069-DF-", s)
    s = re.sub(r"0-069-1S5-", "0-069-1S-", s)

    # Fix 0-069.MS → 0-069-MS (dot instead of dash)
    s = re.sub(r"0-069\.([A-Z])", r"0-069-\1", s)

    # Fix 0-D69 → 0-069 (D instead of 0 in section number)
    s = re.sub(r"0-D69-", "0-069-", s)

    # Fix DM-D454 → DM-0454, PP-D0037 → PP-0037 (D instead of 0 in number part)
    s = re.sub(r"(0-069-[A-Z]{2}-)D(\d{3,4})", r"\g<1>0\2", s)
    s = re.sub(r"(0-069-[A-Z]{2}-)D0+(\d{3,4})", r"\g<1>\2", s)

    # Fix space in code number: '01 14' → '0114', 'J1- 1004' → 'J1-1004'
    s = re.sub(r"(0-069-[A-Z\d]{2}-)\s+(\d)", r"\1\2", s)
    s = re.sub(r"(0-069-[A-Z]{2}-\d{2})\s+(\d{2})\b", r"\1\2", s)

    # Fix bare '0-069-1-' → '0-069-J1-' (missing J, OCR dropped it)
    s = re.sub(r"0-069-1-(\d{4})", r"0-069-J1-\1", s)

    # Fix '0-069-.1-' → '0-069-J1-' (dot instead of J)
    s = re.sub(r"0-069-\.1-", "0-069-J1-", s)

    # Fix '0-069-,)I-' → '0-069-JI-'
    s = re.sub(r"0-069-[,.]?\)?[I1]-", "0-069-J1-", s)
    s = re.sub(r"0-069-,\)I-", "0-069-JI-", s)

    # Fix '0-069-M-' (single letter, missing S) → '0-069-MS-'
    s = re.sub(r"0-069-M-(\d{4})", r"0-069-MS-\1", s)

    # Fix ££ → EE (double pound sign)
    s = s.replace("££", "EE")

    # Fix 0-089-.1 → 0-089-J1
    s = re.sub(r"0-089-\.1-", "0-089-J1-", s)

    # Fix ,1- → J1- (generic catch-all at end)
    s = re.sub(r"(0-0[6-8]9-),1-", r"\g<1>J1-", s)

    return s


def parse_line(line: str, last_mesa: int = 1) -> dict | None:
    """Try to parse a single padron line into a structured record."""
    cleaned = sanitize_line(line)
    if not cleaned:
        return None

    for pattern in PATTERNS:
        m = pattern.match(cleaned)
        if m:
            return {
                "tipo": m.group(1).upper(),
                "documento": re.sub(r"[^\d]", "", m.group(2)),
                "nombre": m.group(3).strip(),
                "distrito_escuela": normalize_distrito(m.group(4).strip()),
                "mesa": int(m.group(5)),
            }

    # Rescue: we matched TIPO+DOC+NAME+DISTRITO but mesa number is garbled
    m = RESCUE_PATTERN.match(cleaned)
    if m:
        return {
            "tipo": m.group(1).upper(),
            "documento": re.sub(r"[^\d]", "", m.group(2)),
            "nombre": m.group(3).strip(),
            "distrito_escuela": normalize_distrito(m.group(4).strip()),
            "mesa": last_mesa,  # Use context from previous records
        }

    return None


def normalize_distrito(raw: str) -> str:
    """Normalize DISTRITO-ESCUELA values to handle OCR inconsistencies."""
    upper = raw.upper().strip()
    if "JUBILAD" in upper:
        return "JUBILADO/A"
    if "SEDE" in upper:
        return "AP. EN SEDE"
    # Normalize establishment codes: replace O with 0 in numeric positions
    if re.match(r"^[\dO]-[\dO]{2,3}-[A-Z\d]{2}-[\dO]{3,4}$", upper):
        return upper.replace("O", "0")
    return upper


def extract_mesa_header(text: str) -> tuple[str | None, str | None]:
    """Extract MESA number and name from page header text."""
    m = MESA_HEADER.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def parse_page_range(page_str: str, max_pages: int) -> tuple[int, int]:
    """Parse page range string like '1-5' or '10' into (start, end)."""
    if "-" in page_str:
        parts = page_str.split("-", 1)
        start = max(1, int(parts[0]))
        end = min(max_pages, int(parts[1]))
    else:
        start = max(1, int(page_str))
        end = start
    return start, end


def process_pdf(
    pdf_path: str,
    output_dir: str,
    dpi: int = 300,
    page_range: str | None = None,
    batch_size: int = 10,
) -> pd.DataFrame:
    """Process the scanned padron PDF and extract structured data."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"ERROR: No se encontró el archivo: {pdf_path}")
        sys.exit(1)

    # --- Get PDF info ---
    info = pdfinfo_from_path(str(pdf_path))
    total_pages = info["Pages"]

    if page_range:
        first_page, last_page = parse_page_range(page_range, total_pages)
    else:
        first_page, last_page = 1, total_pages

    pages_to_process = last_page - first_page + 1

    print(f"  Archivo:  {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  Paginas:  {pages_to_process} de {total_pages} (rango: {first_page}-{last_page})")
    print(f"  DPI:      {dpi}")
    print(f"  Output:   {output_dir.resolve()}\n")

    all_records: list[dict] = []
    failed_lines: list[tuple[int, str]] = []
    current_mesa_name: str | None = None
    last_mesa: int = 1  # Track last seen mesa for rescue parsing

    # --- Process page by page in batches (memory efficient) ---
    tesseract_config = "--oem 3 --psm 6"

    with tqdm(total=pages_to_process, desc="OCR", unit="pag") as pbar:
        for batch_start in range(first_page, last_page + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, last_page)

            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=batch_start,
                last_page=batch_end,
                fmt="jpeg",
            )

            for i, image in enumerate(images):
                page_num = batch_start + i
                text = pytesseract.image_to_string(image, lang="spa", config=tesseract_config)
                lines = text.strip().split("\n")

                # Check for mesa header change
                mesa_num, mesa_name = extract_mesa_header(text)
                if mesa_name:
                    current_mesa_name = mesa_name
                if mesa_num:
                    last_mesa = int(mesa_num)

                page_count = 0
                for line in lines:
                    record = parse_line(line, last_mesa=last_mesa)
                    if record:
                        record["seccion"] = current_mesa_name or ""
                        record["pagina_pdf"] = page_num
                        all_records.append(record)
                        last_mesa = record["mesa"]  # Update context
                        page_count += 1
                    elif PARTIAL_LINE.match(line.strip()):
                        failed_lines.append((page_num, line.strip()))

                pbar.set_postfix(registros=len(all_records), pag=page_num)
                pbar.update(1)

            # Free memory
            del images

    # --- Results ---
    print(f"\n  OCR completado!")
    print(f"  Registros extraidos: {len(all_records)}")
    print(f"  Lineas no parseadas: {len(failed_lines)}")

    if not all_records:
        print("\n  ERROR: No se extrajeron registros. Verifica el PDF.")
        sys.exit(1)

    # --- Build DataFrame ---
    df = pd.DataFrame(all_records)
    column_order = ["tipo", "documento", "nombre", "distrito_escuela", "mesa", "seccion", "pagina_pdf"]
    df = df[column_order]

    # --- Export ---
    print(f"\n  Exportando datos...")

    csv_path = output_dir / "padron.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"    CSV:  {csv_path.name} ({csv_path.stat().st_size / 1024:.0f} KB)")

    json_path = output_dir / "padron.json"
    records_json = df.to_dict(orient="records")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records_json, f, ensure_ascii=False, indent=2)
    print(f"    JSON: {json_path.name} ({json_path.stat().st_size / 1024:.0f} KB)")

    xlsx_path = output_dir / "padron.xlsx"
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(f"    XLSX: {xlsx_path.name} ({xlsx_path.stat().st_size / 1024:.0f} KB)")

    # --- Save errors for review ---
    if failed_lines:
        errors_path = output_dir / "errores_ocr.txt"
        with open(errors_path, "w", encoding="utf-8") as f:
            for page, line in failed_lines:
                f.write(f"Pag {page}: {line}\n")
        print(f"    Errores: {errors_path.name} ({len(failed_lines)} lineas)")

    # --- Summary ---
    print(f"\n  RESUMEN")
    print(f"  {'─' * 40}")
    print(f"  Total registros:  {len(df)}")
    print(f"  Tipos doc:        {dict(df['tipo'].value_counts())}")
    print(f"  Mesas:            {sorted(df['mesa'].unique().tolist())}")
    print(f"  Distritos:        {df['distrito_escuela'].unique().tolist()}")
    print(f"  Secciones:        {df['seccion'].unique().tolist()}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Procesador de Padron Electoral SUTEBA — OCR de PDFs escaneados"
    )
    parser.add_argument("--input", "-i", required=True, help="Ruta al PDF del padron")
    parser.add_argument("--output", "-o", default="./output", help="Directorio de salida (default: ./output)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI para conversion (default: 300)")
    parser.add_argument("--pages", "-p", default=None, help="Rango de paginas: '1-5' o '10' (default: todas)")
    parser.add_argument("--batch", "-b", type=int, default=10, help="Paginas por lote en memoria (default: 10)")

    args = parser.parse_args()

    print(f"\n  PROCESADOR DE PADRON SUTEBA")
    print(f"  {'=' * 40}\n")

    process_pdf(
        pdf_path=args.input,
        output_dir=args.output,
        dpi=args.dpi,
        page_range=args.pages,
        batch_size=args.batch,
    )

    print(f"\n  Listo!\n")


if __name__ == "__main__":
    main()
