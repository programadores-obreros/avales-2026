#!/usr/bin/env python3
"""
Cruza padron 2026 (OCR reconstruido) contra padron 2022 (oficial, confiable).
- Corrige nombres usando el dato 2022 para DNIs que matchean
- Agrega escuela_2022 y escuela_2026 en todos los registros
- No toca registros sin match de DNI
"""

import csv
import json
import os
from collections import defaultdict
from difflib import SequenceMatcher

PADRON_2022 = "/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/pradones/output_claude/padron_2022_claude.csv"
PADRON_2026 = "preproduccion/padron_cruzado.json"
OUTPUT_DIR = "preproduccion"


def norm_dni(d):
    return (d or "").strip().replace(".", "").replace(" ", "")


def similitud(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def tiene_basura(nombre):
    """Detecta artefactos de OCR en el nombre."""
    basura = ["$", "[", "]", ";", "{", "}", "|", "\\", "@", "#", "%"]
    return any(c in nombre for c in basura)


def es_mejor_nombre(nombre_22, nombre_26):
    """Decide si el nombre del 2022 es mejor que el del 2026.
    Solo corrige si el 2022 no tiene basura y es razonablemente mejor."""
    if not nombre_22:
        return False
    if tiene_basura(nombre_22):
        return False
    if not nombre_26:
        return True
    # Si el 2026 tiene basura y el 2022 no, corregir
    if tiene_basura(nombre_26) and not tiene_basura(nombre_22):
        return True
    # Si el 2022 es más completo (más largo) y similar
    if len(nombre_22) > len(nombre_26) + 2:
        return True
    # Si son similares, preferir el que tenga tildes (más completo)
    tildes_22 = sum(1 for c in nombre_22 if c in "ÁÉÍÓÚÑ")
    tildes_26 = sum(1 for c in nombre_26 if c in "ÁÉÍÓÚÑ")
    if tildes_22 > tildes_26:
        return True
    return False


def main():
    # Cargar 2022
    with open(PADRON_2022, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        datos_2022 = list(reader)

    idx22 = {}
    for r in datos_2022:
        d = norm_dni(r.get("DOCUMENTO", "") or r.get("documento", ""))
        if d:
            idx22[d] = r

    # Cargar 2026
    with open(PADRON_2026, "r", encoding="utf-8") as f:
        datos_2026 = json.load(f)["registros"]

    # Stats
    stats = {
        "total_2026": len(datos_2026),
        "match_dni": 0,
        "nombre_exacto": 0,
        "nombre_corregido": 0,
        "nombre_muy_distinto": 0,
        "sin_match": 0,
        "escuela_igual": 0,
        "escuela_cambio": 0,
        "escuela_2026_vacia": 0,
    }

    resultado = []
    correcciones_log = []

    for r26 in datos_2026:
        dni = norm_dni(r26.get("dni", ""))
        nombre_26 = (r26.get("nombre", "") or "").strip()
        escuela_26 = (r26.get("escuela", "") or "").strip()

        reg = {
            "dni": r26.get("dni", ""),
            "tipo": r26.get("tipo", "DNI"),
            "nombre": nombre_26,
            "nombre_corregido": False,
            "nombre_original_ocr": "",
            "escuela_2026": escuela_26,
            "escuela_2022": "",
            "observacion": r26.get("observacion", ""),
            "pagina": r26.get("pagina", ""),
            "pagina_confirmada": r26.get("pagina_confirmada", False),
            "fuente": r26.get("_fuente", ""),
        }

        if dni and dni in idx22:
            r22 = idx22[dni]
            stats["match_dni"] += 1

            nombre_22 = (r22.get("NOMBRE", "") or r22.get("nombre", "") or "").strip()
            escuela_22 = (r22.get("ESCUELA", "") or r22.get("distrito_escuela", "") or "").strip()

            reg["escuela_2022"] = escuela_22

            # Comparar nombres
            sim = similitud(nombre_22, nombre_26)

            if nombre_22.upper() == nombre_26.upper():
                stats["nombre_exacto"] += 1
            elif sim > 0.6 and es_mejor_nombre(nombre_22, nombre_26):
                # 2022 es mejor y no tiene basura: corregir
                reg["nombre"] = nombre_22
                reg["nombre_corregido"] = True
                reg["nombre_original_ocr"] = nombre_26
                stats["nombre_corregido"] += 1
                correcciones_log.append({
                    "dni": dni,
                    "ocr": nombre_26,
                    "corregido": nombre_22,
                    "similitud": round(sim, 2),
                    "pagina": r26.get("pagina", ""),
                })
            elif sim > 0.6:
                # Similar pero 2022 no es claramente mejor (tiene basura, etc)
                stats["nombre_exacto"] += 1  # lo contamos como OK
                correcciones_log.append({
                    "dni": dni,
                    "ocr_2026": nombre_26,
                    "ref_2022": nombre_22,
                    "similitud": round(sim, 2),
                    "pagina": r26.get("pagina", ""),
                    "nota": "2022 tiene artefactos, se mantiene 2026",
                })
            else:
                # Muy distinto: posible DNI mal leído
                stats["nombre_muy_distinto"] += 1
                correcciones_log.append({
                    "dni": dni,
                    "ocr": nombre_26,
                    "ref_2022": nombre_22,
                    "similitud": round(sim, 2),
                    "pagina": r26.get("pagina", ""),
                    "warning": "nombre muy distinto, posible DNI erroneo",
                })

            # Comparar escuelas
            if not escuela_26:
                stats["escuela_2026_vacia"] += 1
            elif escuela_26 == escuela_22:
                stats["escuela_igual"] += 1
            else:
                stats["escuela_cambio"] += 1
        else:
            stats["sin_match"] += 1

        resultado.append(reg)

    # Ordenar por nombre
    resultado.sort(key=lambda r: r.get("nombre", ""))

    # Guardar JSON
    json_path = os.path.join(OUTPUT_DIR, "padron_validado.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_registros": len(resultado),
            "stats": stats,
            "registros": resultado,
        }, f, ensure_ascii=False, indent=2)

    # Guardar CSV
    csv_path = os.path.join(OUTPUT_DIR, "padron_validado.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "TIPO", "DNI", "APELLIDO_NOMBRE", "NOMBRE_CORREGIDO",
            "NOMBRE_ORIGINAL_OCR", "ESCUELA_2026", "ESCUELA_2022",
            "OBSERVACION", "PAGINA", "FUENTE",
        ])
        for r in resultado:
            writer.writerow([
                r["tipo"],
                r["dni"],
                r["nombre"],
                "SI" if r["nombre_corregido"] else "",
                r["nombre_original_ocr"],
                r["escuela_2026"],
                r["escuela_2022"],
                r["observacion"],
                r["pagina"],
                r["fuente"],
            ])

    # Guardar log de correcciones
    log_path = os.path.join(OUTPUT_DIR, "correcciones_nombre.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(correcciones_log, f, ensure_ascii=False, indent=2)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  CRUCE 2022 vs 2026 - RESULTADO")
    print(f"{'='*60}")
    print(f"  Total registros 2026:       {stats['total_2026']}")
    print(f"  Match por DNI con 2022:     {stats['match_dni']}")
    print(f"  Sin match (nuevos 2026):    {stats['sin_match']}")
    print(f"")
    print(f"  --- NOMBRES ---")
    print(f"  Exactos (sin cambio):       {stats['nombre_exacto']}")
    print(f"  Corregidos con 2022:        {stats['nombre_corregido']}")
    print(f"  Muy distintos (no tocados): {stats['nombre_muy_distinto']}")
    print(f"")
    print(f"  --- ESCUELAS ---")
    print(f"  Misma escuela 2022=2026:    {stats['escuela_igual']}")
    print(f"  Cambio de escuela:          {stats['escuela_cambio']}")
    print(f"  Sin escuela en 2026:        {stats['escuela_2026_vacia']}")
    print(f"")
    print(f"  Archivos generados:")
    print(f"    {json_path}")
    print(f"    {csv_path}")
    print(f"    {log_path} ({len(correcciones_log)} entradas)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
