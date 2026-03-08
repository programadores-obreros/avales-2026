#!/usr/bin/env python3
"""
Procesa el padrón 2022 con Claude Vision - versión RÁPIDA.
Usa imágenes pre-extraídas (pages_crop/) y procesamiento paralelo.
"""

import base64
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

CROP_DIR = "pages_crop"
OUTPUT_DIR = "output_claude"
TOTAL_PAGES = 172
WORKERS = 5  # 5 threads paralelos

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


def process_page(client, pag):
    """Procesa una página. Retorna (pag, registros, error)."""
    pag_str = str(pag).zfill(3)
    csv_path = os.path.join(OUTPUT_DIR, f"pag_{pag_str}_datos.csv")

    # Skip si ya procesada
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return (pag, rows, None, True)

    img_path = os.path.join(CROP_DIR, f"page_{pag_str}.jpg")
    if not os.path.exists(img_path):
        return (pag, [], f"Imagen no encontrada: {img_path}", False)

    with open(img_path, "rb") as f:
        img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    for attempt in range(3):
        try:
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

            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            registros = json.loads(text)

            # Guardar CSV
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["TIPO", "DOCUMENTO", "NOMBRE", "ESCUELA", "MESA"])
                writer.writeheader()
                for r in registros:
                    writer.writerow({
                        "TIPO": r.get("tipo", "DNI"),
                        "DOCUMENTO": r.get("documento", ""),
                        "NOMBRE": r.get("nombre", ""),
                        "ESCUELA": r.get("escuela", ""),
                        "MESA": r.get("mesa", ""),
                    })

            # Guardar OCR raw
            with open(os.path.join(OUTPUT_DIR, f"pag_{pag_str}_ocr.txt"), "w") as f:
                f.write(response.content[0].text)

            return (pag, registros, None, False)

        except anthropic.RateLimitError:
            wait = 15 * (attempt + 1)
            time.sleep(wait)
        except json.JSONDecodeError as e:
            # Guardar raw para debug
            with open(os.path.join(OUTPUT_DIR, f"pag_{pag_str}_raw.txt"), "w") as f:
                f.write(response.content[0].text)
            return (pag, [], f"JSON parse error: {e}", False)
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                return (pag, [], str(e), False)

    return (pag, [], "Max retries exceeded", False)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY no configurada")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"\n{'='*60}")
    print(f"  PROCESAMIENTO PADRON 2022 - FAST (5 workers)")
    print(f"{'='*60}")
    print(f"  Imágenes: {CROP_DIR}/ ({TOTAL_PAGES} páginas)")
    print(f"  Output: {OUTPUT_DIR}/\n")

    total_regs = 0
    errores = 0
    all_records = []
    skipped = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(process_page, client, pag): pag
            for pag in range(1, TOTAL_PAGES + 1)
        }

        for future in as_completed(futures):
            pag, registros, error, was_cached = future.result()

            if error:
                print(f"  [{pag:3d}/{TOTAL_PAGES}] ERROR: {error}")
                errores += 1
            elif was_cached:
                skipped += 1
                total_regs += len(registros)
                for r in registros:
                    r["pagina_pdf"] = pag
                    all_records.append(r)
            else:
                total_regs += len(registros)
                for r in registros:
                    row = {
                        "TIPO": r.get("tipo", "DNI"),
                        "DOCUMENTO": r.get("documento", ""),
                        "NOMBRE": r.get("nombre", ""),
                        "ESCUELA": r.get("escuela", ""),
                        "MESA": r.get("mesa", ""),
                        "pagina_pdf": pag,
                    }
                    all_records.append(row)
                print(f"  [{pag:3d}/{TOTAL_PAGES}] {len(registros)} registros OK")

    # Ordenar por página
    all_records.sort(key=lambda r: int(r.get("pagina_pdf", 0)))

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
    print(f"  Ya procesadas (skip): {skipped}")
    print(f"  Errores: {errores}")
    print(f"  Archivos: {json_path}")
    print(f"            {csv_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
