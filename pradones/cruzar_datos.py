#!/usr/bin/env python3
"""
Cruce de datos: Padrón OCR + Zonas + Sedes

Unifica toda la información electoral SUTEBA:
- Padrón OCR (votantes con escuela y mesa)
- Zonas (qué mesas pertenecen a cada zona)
- Circuitos (qué escuelas votan en cada mesa/sede)

Uso:
    python cruzar_datos.py --padron output/padron.csv \
                           --zonas "Zonas elección Suteba 2022.xlsx" \
                           --sedes padrones_por_escuela.xls \
                           --output output/
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# 1. PARSER DE ZONAS — extrae zona → mesa → escuelas de cada sheet
# ---------------------------------------------------------------------------

def parse_zona_sheet(df: pd.DataFrame, sheet_name: str) -> list[dict]:
    """Parse a single zona sheet into a list of mesa records.

    Each record: {zona, zona_nombre, mesa, escuela_sede, direccion, localidad, escuelas: []}
    """
    # Extract zona name from row 2 (e.g., "ZONA 6: Catán sur")
    zona_raw = None
    for i in range(min(5, len(df))):
        val = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else ""
        if "ZONA" in val.upper():
            zona_raw = val.strip()
            break

    if not zona_raw:
        zona_raw = sheet_name.strip()

    # Parse zona number and name
    m = re.match(r"ZONA\s*(\d+)[:\s]*(.*)", zona_raw, re.IGNORECASE)
    if m:
        zona_num = int(m.group(1))
        zona_nombre = m.group(2).strip()
    else:
        zona_num = 0
        zona_nombre = zona_raw

    # Walk through rows looking for mesa entries (M###) and their escuelas
    mesas = []
    current_mesa = None

    for _, row in df.iterrows():
        col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        col1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        col2 = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        col3 = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
        col4 = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""

        # Skip headers
        if col0.upper() in ("", "NaN", "Nº MESA", "ELECCIONES SUTEBA 2022- LISTA MULTICOLOR"):
            # But if col4 has escuela data and we have a current mesa, capture it
            if col0 == "" and col4 and col4 != "nan" and col4 != "NaN" and current_mesa:
                escuela = col4.strip()
                if escuela.lower() not in ("escuelas que votan", "nan"):
                    current_mesa["escuelas"].append(escuela)
            continue

        if "ZONA" in col0.upper() or "Responsable" in col0:
            continue

        # Check if this is a mesa row (M### pattern)
        mesa_match = re.match(r"M\s*(\d+)", col0)
        if mesa_match:
            if current_mesa:
                mesas.append(current_mesa)

            current_mesa = {
                "zona": zona_num,
                "zona_nombre": zona_nombre,
                "mesa": int(mesa_match.group(1)),
                "escuela_sede": col1 if col1 != "nan" else "",
                "direccion": col2 if col2 != "nan" else "",
                "localidad": col3 if col3 != "nan" else "",
                "escuelas": [],
            }

            # col4 might have first escuela on same row
            if col4 and col4 != "nan" and col4.lower() != "escuelas que votan":
                current_mesa["escuelas"].append(col4.strip())

        elif current_mesa and col4 and col4 != "nan":
            # Escuela row (continuation)
            current_mesa["escuelas"].append(col4.strip())

    # Don't forget the last mesa
    if current_mesa:
        mesas.append(current_mesa)

    return mesas


def parse_all_zonas(zonas_path: str) -> pd.DataFrame:
    """Parse all zona sheets and return a flat DataFrame."""
    xls = pd.ExcelFile(zonas_path, engine="openpyxl")
    all_mesas = []

    for sheet_name in xls.sheet_names:
        if sheet_name.upper() == "RESUMEN":
            continue

        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        mesas = parse_zona_sheet(df, sheet_name)
        all_mesas.extend(mesas)

    return all_mesas


# ---------------------------------------------------------------------------
# 2. NORMALIZACIÓN DE CÓDIGOS DE ESCUELA
# ---------------------------------------------------------------------------

def normalize_escuela_code(raw: str) -> str:
    """Normalize a school code from the zonas file to match OCR format.

    Zonas format:  PP106, MS20, JI912, DM494, T3, CEA735/6
    OCR format:    0-069-PP-0106, 0-069-MS-0020, 0-069-JI-0912

    Returns the normalized code WITHOUT the 0-069- prefix.
    """
    s = raw.strip().upper()

    # Remove spaces within code: "MS 20" → "MS20", "PP 106" → "PP106"
    s = re.sub(r"^([A-Z]+)\s+(\d+)", r"\1\2", s)

    # Remove descriptions after code: "DE770 ESC ADULTOD 770" → "DE770"
    # "MF15 CENTRO EDUC AGRICOLA 15" → "MF15"
    s = re.sub(r"^([A-Z]+\d+)\s+.*", r"\1", s)

    # Handle special compound codes: "CEA735/6" → keep as is
    # Handle "MSS 52" → "MS52" (typo with double S)
    s = re.sub(r"^MSS\s*", "MS", s)

    # Handle "MS 20" → "MS20"
    s = re.sub(r"^([A-Z]{1,3})\s+(\d+)", r"\1\2", s)

    # Extract letter prefix and number
    m = re.match(r"^([A-Z]{1,4})(\d+)(?:/.*)?$", s)
    if not m:
        return s  # Can't normalize — return as-is (JUBILADOS, PAGO EN SEDE, etc.)

    prefix = m.group(1)
    number = m.group(2)

    # Pad number to 4 digits
    number_padded = number.zfill(4)

    return f"{prefix}-{number_padded}"


def normalize_ocr_distrito(code: str) -> str:
    """Normalize an OCR distrito_escuela code to just the PREFIX-NUMBER part.

    OCR format: 0-069-PP-0106 → PP-0106
    """
    if not code or code in ("JUBILADO/A", "AP. EN SEDE"):
        return code

    m = re.match(r"^\d-\d{3}-([A-Z\d]+-\d+)$", code)
    if m:
        return m.group(1)
    return code


# ---------------------------------------------------------------------------
# 3. CRUCE DE DATOS
# ---------------------------------------------------------------------------

def build_escuela_mesa_mapping(mesas_data: list[dict]) -> pd.DataFrame:
    """Build a flat table: escuela_code → mesa, zona, sede info."""
    rows = []
    for mesa in mesas_data:
        for escuela_raw in mesa["escuelas"]:
            code = normalize_escuela_code(escuela_raw)
            rows.append({
                "escuela_code": code,
                "escuela_raw": escuela_raw,
                "mesa": mesa["mesa"],
                "zona": mesa["zona"],
                "zona_nombre": mesa["zona_nombre"],
                "escuela_sede": mesa["escuela_sede"],
                "direccion": mesa["direccion"],
                "localidad": mesa["localidad"],
            })

    return pd.DataFrame(rows)


def cruzar_todo(
    padron_path: str,
    zonas_path: str,
    sedes_path: str,
    output_dir: str,
):
    """Main function: cross-reference all data sources."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load padrón OCR ---
    print("  Cargando padron OCR...")
    padron = pd.read_csv(padron_path)
    print(f"    {len(padron)} votantes")

    # --- Parse zonas ---
    print("  Parseando zonas...")
    mesas_data = parse_all_zonas(zonas_path)
    print(f"    {len(mesas_data)} mesas en {len(set(m['zona'] for m in mesas_data))} zonas")

    # --- Build escuela → mesa mapping ---
    print("  Construyendo mapeo escuela → mesa...")
    escuela_map = build_escuela_mesa_mapping(mesas_data)
    print(f"    {len(escuela_map)} asignaciones escuela→mesa")

    # --- Load sedes ---
    print("  Cargando sedes...")
    sedes = pd.read_excel(sedes_path)
    print(f"    {len(sedes)} sedes")

    # --- Normalize OCR distrito codes ---
    padron["escuela_code"] = padron["distrito_escuela"].apply(normalize_ocr_distrito)

    # Handle JI vs J1 (OCR reads I as 1)
    # Create alternate codes for matching
    escuela_map["escuela_code_alt"] = escuela_map["escuela_code"].str.replace("JI-", "J1-", regex=False)

    # --- Merge: padron + escuela_map ---
    print("  Cruzando datos...")

    # Deduplicate escuela_map (same code can appear from OCR variations)
    merge_cols = ["escuela_code", "mesa", "zona", "zona_nombre", "escuela_sede", "direccion", "localidad"]
    escuela_map_dedup = escuela_map[merge_cols].drop_duplicates(subset=["escuela_code"]).copy()

    # First try direct match
    merged = padron.merge(
        escuela_map_dedup.rename(columns={"mesa": "mesa_sede", "localidad": "localidad_sede"}),
        on="escuela_code",
        how="left",
    )

    # For unmatched, try JI↔J1 alternate
    unmatched_mask = merged["zona"].isna()
    if unmatched_mask.sum() > 0:
        # Build alt map: JI→J1
        alt_map = escuela_map_dedup.copy()
        alt_map["escuela_code"] = alt_map["escuela_code"].str.replace("JI-", "J1-", regex=False)
        alt_map = alt_map.drop_duplicates(subset=["escuela_code"])

        # Re-merge unmatched rows
        unmatched_df = merged.loc[unmatched_mask, ["escuela_code"]].copy()
        alt_result = unmatched_df.merge(
            alt_map.rename(columns={"mesa": "mesa_sede", "localidad": "localidad_sede"}),
            on="escuela_code",
            how="left",
        )

        for col in ["mesa_sede", "zona", "zona_nombre", "escuela_sede", "direccion", "localidad_sede"]:
            merged.loc[unmatched_mask, col] = alt_result[col].values

    # Also try M3→MS, M5→MS, M8→MS (common OCR errors in distrito codes)
    for ocr_err, correct in [("M3-", "MS-"), ("M5-", "MS-"), ("M8-", "MS-")]:
        still_unmatched = merged["zona"].isna()
        if still_unmatched.sum() == 0:
            break

        fix_map = escuela_map_dedup.copy()
        unmatched_df = merged.loc[still_unmatched, ["escuela_code"]].copy()
        unmatched_df["escuela_code_fix"] = unmatched_df["escuela_code"].str.replace(ocr_err, correct, regex=False)

        fix_result = unmatched_df.merge(
            fix_map.rename(columns={"escuela_code": "escuela_code_fix", "mesa": "mesa_sede", "localidad": "localidad_sede"}),
            on="escuela_code_fix",
            how="left",
        )

        fix_matched = fix_result["zona"].notna()
        if fix_matched.sum() > 0:
            idx = merged.index[still_unmatched]
            for col in ["mesa_sede", "zona", "zona_nombre", "escuela_sede", "direccion", "localidad_sede"]:
                merged.loc[idx[fix_matched.values], col] = fix_result.loc[fix_matched, col].values

    # --- Stats ---
    matched = merged["zona"].notna()
    jubilados = padron["distrito_escuela"].isin(["JUBILADO/A", "AP. EN SEDE"])

    print(f"\n  RESULTADO DEL CRUCE")
    print(f"  {'─' * 50}")
    print(f"  Total votantes:            {len(merged)}")
    print(f"  Matcheados con zona:       {matched.sum()}")
    print(f"  Jubilados/AP en Sede:      {jubilados.sum()} (mesa 1, no tienen escuela)")
    print(f"  Sin zona asignada:         {(~matched & ~jubilados).sum()}")

    # --- Export: Padrón completo enriquecido ---
    print(f"\n  Exportando...")

    # 1. Padrón completo con zona
    padron_full = merged.copy()
    padron_full["zona"] = padron_full["zona"].fillna(0).astype(int)
    padron_full["mesa_sede"] = padron_full["mesa_sede"].fillna(padron_full["mesa"]).astype(int)

    export_cols = [
        "tipo", "documento", "nombre", "distrito_escuela", "escuela_code",
        "mesa_sede", "zona", "zona_nombre", "escuela_sede", "direccion",
        "localidad_sede", "pagina_pdf",
    ]
    padron_full[export_cols].to_csv(output_dir / "padron_completo.csv", index=False)
    padron_full[export_cols].to_excel(output_dir / "padron_completo.xlsx", index=False, engine="openpyxl")
    print(f"    padron_completo.csv/xlsx ({len(padron_full)} registros)")

    # 2. Resumen por zona
    zona_summary = (
        padron_full[padron_full["zona"] > 0]
        .groupby(["zona", "zona_nombre"])
        .agg(
            votantes=("documento", "count"),
            mesas=("mesa_sede", "nunique"),
            escuelas=("escuela_code", "nunique"),
        )
        .reset_index()
        .sort_values("zona")
    )
    zona_summary.to_csv(output_dir / "resumen_por_zona.csv", index=False)
    print(f"    resumen_por_zona.csv ({len(zona_summary)} zonas)")

    # 3. Resumen por mesa
    mesa_summary = (
        padron_full[padron_full["zona"] > 0]
        .groupby(["mesa_sede", "zona", "zona_nombre", "escuela_sede", "direccion", "localidad_sede"])
        .agg(
            votantes=("documento", "count"),
            escuelas=("escuela_code", "nunique"),
            lista_escuelas=("escuela_code", lambda x: ", ".join(sorted(x.unique()))),
        )
        .reset_index()
        .sort_values("mesa_sede")
    )
    mesa_summary.to_csv(output_dir / "resumen_por_mesa.csv", index=False)
    print(f"    resumen_por_mesa.csv ({len(mesa_summary)} mesas)")

    # 4. Mapeo escuela → mesa (para referencia)
    escuela_map.to_csv(output_dir / "mapeo_escuela_mesa.csv", index=False)
    print(f"    mapeo_escuela_mesa.csv ({len(escuela_map)} asignaciones)")

    # 5. Votantes sin zona (para debug)
    sin_zona = merged[(~matched) & (~jubilados)]
    if len(sin_zona) > 0:
        sin_zona_codes = sin_zona["escuela_code"].value_counts().reset_index()
        sin_zona_codes.columns = ["escuela_code", "votantes"]
        sin_zona_codes.to_csv(output_dir / "escuelas_sin_zona.csv", index=False)
        print(f"    escuelas_sin_zona.csv ({len(sin_zona_codes)} códigos sin mapear, {len(sin_zona)} votantes)")

    # --- Print zona summary ---
    print(f"\n  RESUMEN POR ZONA")
    print(f"  {'─' * 60}")
    print(f"  {'Zona':<6} {'Nombre':<30} {'Votantes':>9} {'Mesas':>6}")
    print(f"  {'─' * 60}")
    for _, row in zona_summary.iterrows():
        print(f"  {int(row['zona']):<6} {row['zona_nombre'][:30]:<30} {int(row['votantes']):>9} {int(row['mesas']):>6}")
    print(f"  {'─' * 60}")
    print(f"  {'TOTAL':<37} {int(zona_summary['votantes'].sum()):>9} {int(zona_summary['mesas'].sum()):>6}")

    return padron_full, escuela_map, zona_summary, mesa_summary


def main():
    parser = argparse.ArgumentParser(description="Cruce de datos Padron SUTEBA + Zonas + Sedes")
    parser.add_argument("--padron", "-p", required=True, help="CSV del padron OCR")
    parser.add_argument("--zonas", "-z", required=True, help="XLSX de zonas electorales")
    parser.add_argument("--sedes", "-s", required=True, help="XLS de sedes/escuelas")
    parser.add_argument("--output", "-o", default="./output", help="Directorio de salida")

    args = parser.parse_args()

    print(f"\n  CRUCE DE DATOS SUTEBA")
    print(f"  {'=' * 50}\n")

    cruzar_todo(
        padron_path=args.padron,
        zonas_path=args.zonas,
        sedes_path=args.sedes,
        output_dir=args.output,
    )

    print(f"\n  Listo!\n")


if __name__ == "__main__":
    main()
