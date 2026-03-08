#!/usr/bin/env python3
"""
Genera los datos y copia imágenes para la herramienta de control web.
Lee padron_2026_final.json (deduplicado, con niveles de confianza),
agrupa por página, y genera control.json.
"""

import json
import os
import shutil
from collections import defaultdict

PREPROD = "preproduccion"
PROCESADO = "procesado"
WEBAPP_DATA = "webapp/public/data"


def main():
    with open(os.path.join(PREPROD, "padron_2026_final.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    registros = data["registros"]
    stats_padron = data["stats"]

    # Agrupar por página
    by_page = defaultdict(list)
    for r in registros:
        by_page[r.get("pagina", 0)].append(r)

    # Preparar directorio de imágenes
    img_dir = os.path.join(WEBAPP_DATA, "procesadas")
    os.makedirs(img_dir, exist_ok=True)

    pages = []
    imagenes_copiadas = 0

    for pag_num in sorted(by_page.keys()):
        regs = by_page[pag_num]
        pag_str = str(pag_num).zfill(4)
        pag_id = f"pag_{pag_str}"

        # Verificar si hay imagen procesada
        img_src = os.path.join(PROCESADO, f"{pag_id}_procesada.png")
        img_path = ""
        if os.path.exists(img_src):
            img_dest = os.path.join(img_dir, f"{pag_id}.png")
            if not os.path.exists(img_dest):
                shutil.copy2(img_src, img_dest)
            img_path = f"data/procesadas/{pag_id}.png"
            imagenes_copiadas += 1

        clean_regs = []
        for r in regs:
            clean_regs.append({
                "dni": r.get("dni", ""),
                "dni_ocr": r.get("dni_original_ocr", ""),
                "dni_corregido": r.get("dni_corregido", False),
                "nombre": r.get("nombre", ""),
                "nombre_ocr": r.get("nombre_original_ocr", ""),
                "nombre_corregido": r.get("nombre_corregido", False),
                "escuela": r.get("escuela_2026", ""),
                "escuela_2022": r.get("escuela_2022", ""),
                "tipo": r.get("tipo", "DNI"),
                "validacion": r.get("validacion", ""),
                "confianza": r.get("confianza", ""),
                "dni_detalle": r.get("dni_detalle", ""),
                "obs": r.get("observacion", ""),
            })

        confirmada = any(r.get("pagina_confirmada") for r in regs)

        pages.append({
            "id": pag_id,
            "numero": pag_num,
            "confirmada": confirmada,
            "imagen": img_path,
            "total": len(clean_regs),
            "registros": clean_regs,
        })

    total_regs = sum(p["total"] for p in pages)
    total_con_imagen = sum(1 for p in pages if p["imagen"])
    total_confirmados = sum(
        sum(1 for r in p["registros"] if r["confianza"] == "CONFIRMADO") for p in pages
    )
    total_alta = sum(
        sum(1 for r in p["registros"] if r["confianza"] == "ALTA") for p in pages
    )
    total_media = sum(
        sum(1 for r in p["registros"] if r["confianza"] == "MEDIA") for p in pages
    )
    total_sin = sum(
        sum(1 for r in p["registros"] if r["validacion"] == "SIN_VALIDAR") for p in pages
    )

    output = {
        "total_registros": total_regs,
        "total_paginas": len(pages),
        "paginas_con_imagen": total_con_imagen,
        "stats": {
            "confirmado": total_confirmados,
            "alta": total_alta,
            "media": total_media,
            "sin_validar": total_sin,
            **stats_padron,
        },
        "pages": pages,
    }

    out_path = os.path.join(WEBAPP_DATA, "control.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)

    print(f"\n{'='*60}")
    print(f"  DATOS DE CONTROL GENERADOS")
    print(f"{'='*60}")
    print(f"  Total páginas:        {len(pages)}")
    print(f"  Total registros:      {total_regs}")
    print(f"  Páginas con imagen:   {total_con_imagen}")
    print(f"  Imágenes copiadas:    {imagenes_copiadas}")
    print(f"  CONFIRMADO:           {total_confirmados}")
    print(f"  ALTA:                 {total_alta}")
    print(f"  MEDIA:                {total_media}")
    print(f"  SIN VALIDAR:          {total_sin}")
    print(f"  JSON size:            {size_mb:.1f} MB")
    print(f"\n  Archivo: {out_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
