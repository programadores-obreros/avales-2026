#!/usr/bin/env python3
"""
Procesa el padrón oficial 2022 (PDF) con Claude Vision.
Extrae cada página como imagen, cropea header/sello, envía a Claude.
"""

import base64
import csv
import json
import os
import subprocess
import sys
import time

import anthropic

PDF_PATH = "padron_oficial.pdf"
OUTPUT_DIR = "output_claude"
TOTAL_PAGES = 172
CROP_TOP_PCT = 0.15  # Sacar 15% superior (header + sello rojo)
DPI = 200            # Suficiente para Claude Vision, ahorra tokens

PROMPT = """Extraé los datos de esta página del padrón electoral SUTEBA 2022.
Cada fila tiene 5 columnas: TIPO (DNI o LC), DOCUMENTO (7-8 dígitos), APELLIDO Y NOMBRE, DISTRITO-ESCUELA, MESA (número).

El DISTRITO-ESCUELA puede ser:
- Código como 0-069-MS-0042, 0-069-PP-0193, 0-069-JI-0905, etc.
- "JUBILADO/A"
- "AP. EN SEDE"

Si hay un header "MESA: X" indicando cambio de mesa, incluí ese número en la columna MESA de las filas siguientes.

Respondé SOLO con un JSON array, sin markdown, con este formato:
[{"tipo": "DNI", "documento": "12345678", "nombre": "APELLIDO NOMBRE", "escuela": "0-069-MS-0042", "mesa": 1}]

Reglas:
- DOCUMENTO siempre 7 u 8 dígitos numéricos
- NOMBRE siempre en MAYÚSCULAS
- Escuela: código 0-069-XX-XXXX, o "JUBILADO/A", o "AP. EN SEDE"
- Si un campo no se lee, dejalo vacío ""
- Extraé TODAS las filas visibles
- Ignorá cualquier sello, logo o marca de agua"""


def extract_page(page_num):
    """Extrae una página del PDF como imagen PNG cropeada."""
    tmp_raw = f"/tmp/p2022_raw_{page_num}.png"
    tmp_crop = f"/tmp/p2022_crop_{page_num}.jpg"

    # PDF page index es 0-based para magick
    idx = page_num - 1
    subprocess.run([
        "magick", "-density", str(DPI),
        f"{PDF_PATH}[{idx}]",
        tmp_raw
    ], check=True, capture_output=True)

    # Leer dimensiones
    result = subprocess.run(
        ["magick", "identify", "-format", "%w %h", tmp_raw],
        capture_output=True, text=True, check=True
    )
    w, h = map(int, result.stdout.strip().split())

    # Crop: sacar top 15%, convertir a JPEG quality 85
    crop_y = int(h * CROP_TOP_PCT)
    crop_h = h - crop_y
    subprocess.run([
        "magick", tmp_raw,
        "-crop", f"{w}x{crop_h}+0+{crop_y}", "+repage",
        "-quality", "85",
        tmp_crop
    ], check=True, capture_output=True)

    # Leer como base64
    with open(tmp_crop, "rb") as f:
        img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    # Limpiar temporales
    os.remove(tmp_raw)
    os.remove(tmp_crop)

    return img_b64


def call_claude(client, img_b64):
    """Envía imagen a Claude Vision y obtiene JSON."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_b64,
                    }
                },
                {"type": "text", "text": PROMPT}
            ]
        }]
    )
    return response.content[0].text


def parse_response(text):
    """Parsea la respuesta JSON de Claude."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY no configurada")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"\n{'='*60}")
    print(f"  PROCESAMIENTO PADRON 2022 CON CLAUDE VISION")
    print(f"{'='*60}")
    print(f"  PDF: {PDF_PATH} ({TOTAL_PAGES} páginas)")
    print(f"  DPI: {DPI}, Crop top: {CROP_TOP_PCT*100:.0f}%")
    print(f"  Modelo: claude-sonnet-4-6")
    print(f"  Output: {OUTPUT_DIR}/\n")

    total_regs = 0
    errores = 0
    all_records = []

    for pag in range(1, TOTAL_PAGES + 1):
        pag_str = str(pag).zfill(3)
        csv_path = os.path.join(OUTPUT_DIR, f"pag_{pag_str}_datos.csv")

        # Skip si ya fue procesada
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            total_regs += len(rows)
            for r in rows:
                r["pagina_pdf"] = pag
                all_records.append(r)
            print(f"  [{pag}/{TOTAL_PAGES}] Ya procesada ({len(rows)} regs) - skip")
            continue

        try:
            # Extraer imagen
            img_b64 = extract_page(pag)

            # Llamar a Claude
            raw = call_claude(client, img_b64)
            registros = parse_response(raw)

            if registros is None:
                print(f"  [{pag}/{TOTAL_PAGES}] ERROR: no se pudo parsear JSON")
                # Guardar raw para debug
                with open(os.path.join(OUTPUT_DIR, f"pag_{pag_str}_raw.txt"), "w") as f:
                    f.write(raw)
                errores += 1
                time.sleep(1)
                continue

            # Guardar CSV
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["TIPO", "DOCUMENTO", "NOMBRE", "ESCUELA", "MESA"])
                writer.writeheader()
                for r in registros:
                    row = {
                        "TIPO": r.get("tipo", "DNI"),
                        "DOCUMENTO": r.get("documento", ""),
                        "NOMBRE": r.get("nombre", ""),
                        "ESCUELA": r.get("escuela", ""),
                        "MESA": r.get("mesa", ""),
                    }
                    writer.writerow(row)
                    row["pagina_pdf"] = pag
                    all_records.append(row)

            # Guardar OCR raw
            with open(os.path.join(OUTPUT_DIR, f"pag_{pag_str}_ocr.txt"), "w") as f:
                f.write(raw)

            total_regs += len(registros)
            print(f"  [{pag}/{TOTAL_PAGES}] {len(registros)} registros OK")

            time.sleep(1)  # Rate limit

        except anthropic.RateLimitError:
            print(f"  [{pag}/{TOTAL_PAGES}] Rate limit - esperando 30s...")
            time.sleep(30)
            pag -= 1  # Retry
            continue
        except Exception as e:
            print(f"  [{pag}/{TOTAL_PAGES}] ERROR: {e}")
            errores += 1
            time.sleep(2)

    # Guardar JSON unificado
    json_path = os.path.join(OUTPUT_DIR, "padron_2022_claude.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_registros": len(all_records),
            "registros": all_records,
        }, f, ensure_ascii=False, indent=2)

    # Guardar CSV unificado
    csv_path = os.path.join(OUTPUT_DIR, "padron_2022_claude.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["TIPO", "DOCUMENTO", "NOMBRE", "ESCUELA", "MESA", "pagina_pdf"])
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n{'='*60}")
    print(f"  RESULTADO")
    print(f"{'='*60}")
    print(f"  Registros totales: {total_regs}")
    print(f"  Errores: {errores}")
    print(f"  Archivos: {json_path}")
    print(f"            {csv_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
