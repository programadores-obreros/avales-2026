#!/usr/bin/env python3
"""
Genera preproduccion/ unificando todos los CSVs buenos de procesado/.
Separa páginas con número real vs hash fallback.
Genera padron_unificado.csv y padron_unificado.json.
"""

import csv
import json
import os
import shutil

PROCESADO = "procesado"
PREPROD = "preproduccion"
UMBRAL_HASH = 200  # páginas > 200 son hash fallback (el padrón no llega a 200)

def main():
    os.makedirs(PREPROD, exist_ok=True)
    os.makedirs(f"{PREPROD}/paginas_ok", exist_ok=True)
    os.makedirs(f"{PREPROD}/paginas_hash", exist_ok=True)

    todas_filas = []
    stats = {"ok": 0, "hash": 0, "vacias": 0, "registros_ok": 0, "registros_hash": 0}

    csvs = sorted([f for f in os.listdir(PROCESADO) if f.endswith("_datos.csv")])

    for csv_file in csvs:
        pag_str = csv_file.replace("pag_", "").replace("_datos.csv", "")
        pag_num = int(pag_str)
        csv_path = os.path.join(PROCESADO, csv_file)

        # Leer registros
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            registros = list(reader)

        # Descartar páginas vacías
        if len(registros) == 0:
            stats["vacias"] += 1
            continue

        # Clasificar: número real vs hash
        es_hash = pag_num >= UMBRAL_HASH
        destino = "paginas_hash" if es_hash else "paginas_ok"

        if es_hash:
            stats["hash"] += 1
            stats["registros_hash"] += len(registros)
        else:
            stats["ok"] += 1
            stats["registros_ok"] += len(registros)

        # Copiar CSV, OCR y PNG
        base = f"pag_{pag_str}"
        for ext in ["_datos.csv", "_ocr.txt", "_procesada.png"]:
            src = os.path.join(PROCESADO, base + ext)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(PREPROD, destino, base + ext))

        # Agregar a lista unificada
        for r in registros:
            r["_pagina"] = pag_num
            r["_pagina_str"] = pag_str
            r["_es_hash"] = es_hash
            todas_filas.append(r)

    # CSV unificado
    csv_unificado = os.path.join(PREPROD, "padron_unificado.csv")
    if todas_filas:
        # Detectar columnas disponibles (puede ser formato viejo o nuevo)
        fieldnames = list(todas_filas[0].keys())
        with open(csv_unificado, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(todas_filas)

    # JSON unificado
    json_unificado = os.path.join(PREPROD, "padron_unificado.json")
    # Limpiar campos internos para el JSON público
    registros_json = []
    for r in todas_filas:
        reg = {
            "pagina": r["_pagina"],
            "pagina_confirmada": not r["_es_hash"],
            "tipo": r.get("TIPO", "DNI"),
            "dni": r.get("DNI", r.get("DOCUMENTO", "")),
            "nombre": r.get("APELLIDO_NOMBRE", r.get("NOMBRE", "")),
            "escuela": r.get("ESCUELA", r.get("DESTINO", "")),
            "observacion": r.get("OBSERVACION", r.get("OBS", "")),
        }
        registros_json.append(reg)

    with open(json_unificado, "w", encoding="utf-8") as f:
        json.dump({
            "total_registros": len(registros_json),
            "paginas_confirmadas": stats["ok"],
            "paginas_hash_pendientes": stats["hash"],
            "paginas_vacias_descartadas": stats["vacias"],
            "registros": registros_json
        }, f, ensure_ascii=False, indent=2)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  PREPRODUCCION GENERADA")
    print(f"{'='*60}")
    print(f"  Páginas con número confirmado: {stats['ok']} ({stats['registros_ok']} registros)")
    print(f"  Páginas con hash (pendientes): {stats['hash']} ({stats['registros_hash']} registros)")
    print(f"  Páginas vacías (descartadas):  {stats['vacias']}")
    print(f"  TOTAL registros:               {stats['registros_ok'] + stats['registros_hash']}")
    print(f"\n  Archivos generados:")
    print(f"    {csv_unificado}")
    print(f"    {json_unificado}")
    print(f"    {PREPROD}/paginas_ok/     ({stats['ok']} páginas)")
    print(f"    {PREPROD}/paginas_hash/   ({stats['hash']} páginas)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
