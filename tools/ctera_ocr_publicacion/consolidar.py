#!/usr/bin/env python3
"""Corre parse_page.py sobre las 12 paginas y consolida en un JSON nacional.
Uso: consolidar.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

def main():
    all_records = []
    resumen = []
    for n in range(1, 13):
        nn = f"{n:02d}"
        txt_path = HERE / f"out_page{nn}_full.txt"
        if not txt_path.exists():
            print(f"AVISO: falta {txt_path}, se omite pagina {n}", file=sys.stderr)
            continue
        result = subprocess.run(
            [sys.executable, str(HERE / "parse_page.py"), str(txt_path), str(n)],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        all_records.extend(data["records"])
        resumen.append({
            "page": n,
            "total_mesas_detectadas": data["total_mesas_detectadas"],
            "marcadas_inciertas_formato": data["marcadas_inciertas_formato"],
            "marcadas_sospechosas_duplicado": data["marcadas_sospechosas_duplicado"],
        })

    n_incierto = sum(1 for r in all_records if r.get("incierto"))
    n_dup = sum(1 for r in all_records if r.get("sospechoso_duplicado"))
    n_limpio = len(all_records) - len(set(
        id(r) for r in all_records if r.get("incierto") or r.get("sospechoso_duplicado")
    ))

    out = {
        "fuente": "ctera/publicacion_elecciones_CTERA_ 2026.pdf (12 paginas, OCR tesseract + rotacion)",
        "total_mesas_detectadas": len(all_records),
        "marcadas_inciertas_formato_total": n_incierto,
        "marcadas_sospechosas_duplicado_total": n_dup,
        "resumen_por_pagina": resumen,
        "records": all_records,
    }
    with open(HERE / "ctera_nacional_mesas.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Total mesas detectadas: {len(all_records)}")
    print(f"Inciertas (formato raro): {n_incierto}")
    print(f"Sospechosas (numero duplicado en la pagina): {n_dup}")
    for r in resumen:
        print(f"  pagina {r['page']:>2}: {r['total_mesas_detectadas']:>3} mesas "
              f"({r['marcadas_inciertas_formato']} inciertas, {r['marcadas_sospechosas_duplicado']} sospechosas)")

if __name__ == "__main__":
    main()
