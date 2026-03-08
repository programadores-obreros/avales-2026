#!/usr/bin/env python3
"""
Cruza preproduccion (primera tanda) vs pts_control (segunda tanda).
Match por DNI, detecta diferencias, completa datos faltantes.
Genera preproduccion/padron_cruzado.json con el resultado final.
"""

import csv
import json
import os
from collections import defaultdict

PROCESADO = "procesado"
PREPROD = "preproduccion"
UMBRAL_HASH = 200

def cargar_preproduccion():
    """Carga el JSON de preproducción (primera tanda)."""
    with open(os.path.join(PREPROD, "padron_unificado.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["registros"]

def cargar_pts_control():
    """Carga todos los CSVs nuevos de pts_control (segunda tanda).
    Identifica cuáles son nuevos comparando timestamps o usando un set conocido."""
    # Los CSVs de primera tanda están en preproduccion/paginas_ok y paginas_hash
    primera_tanda = set()
    for subdir in ["paginas_ok", "paginas_hash"]:
        path = os.path.join(PREPROD, subdir)
        if os.path.exists(path):
            for f in os.listdir(path):
                if f.endswith("_datos.csv"):
                    primera_tanda.add(f)

    # Todos los CSVs en procesado que NO están en primera tanda = pts_control
    registros = []
    paginas_control = 0
    for f in sorted(os.listdir(PROCESADO)):
        if not f.endswith("_datos.csv"):
            continue
        if f in primera_tanda:
            continue

        pag_str = f.replace("pag_", "").replace("_datos.csv", "")
        pag_num = int(pag_str)
        csv_path = os.path.join(PROCESADO, f)

        with open(csv_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        if len(rows) == 0:
            continue

        paginas_control += 1
        es_hash = pag_num >= UMBRAL_HASH

        for r in rows:
            reg = {
                "pagina": pag_num,
                "pagina_confirmada": not es_hash,
                "tipo": r.get("TIPO", "DNI"),
                "dni": r.get("DNI", r.get("DOCUMENTO", "")),
                "nombre": r.get("APELLIDO_NOMBRE", r.get("NOMBRE", "")),
                "escuela": r.get("ESCUELA", r.get("DESTINO", "")),
                "observacion": r.get("OBSERVACION", r.get("OBS", "")),
            }
            registros.append(reg)

    print(f"  pts_control: {paginas_control} páginas, {len(registros)} registros")
    return registros

def normalizar_dni(dni):
    """Normaliza DNI quitando puntos y espacios."""
    if not dni:
        return ""
    return dni.strip().replace(".", "").replace(" ", "")

def tiene_obs_problematica(obs):
    """Chequea si la observación indica dato dudoso."""
    if not obs:
        return False
    obs_lower = obs.lower()
    return any(w in obs_lower for w in ["dudos", "ilegible", "posible", "original", "borroso"])

def elegir_mejor(reg1, reg2):
    """Dados dos registros con mismo DNI, elige el mejor dato campo por campo."""
    mejor = dict(reg1)  # base
    cambios = []

    # Nombre: preferir el más largo (más completo)
    n1 = reg1.get("nombre", "").strip()
    n2 = reg2.get("nombre", "").strip()
    if len(n2) > len(n1) and n2:
        mejor["nombre"] = n2
        cambios.append(f"nombre: '{n1}' -> '{n2}'")

    # Escuela: preferir el que tiene dato vs vacío
    e1 = reg1.get("escuela", "").strip()
    e2 = reg2.get("escuela", "").strip()
    obs1 = reg1.get("observacion", "")
    obs2 = reg2.get("observacion", "")

    if not e1 and e2:
        mejor["escuela"] = e2
        cambios.append(f"escuela: '' -> '{e2}'")
    elif e1 and e2 and e1 != e2:
        # Si uno tiene obs dudosa y el otro no, preferir el sin obs
        if tiene_obs_problematica(obs1) and not tiene_obs_problematica(obs2):
            mejor["escuela"] = e2
            cambios.append(f"escuela: '{e1}' (dudoso) -> '{e2}'")
        elif not tiene_obs_problematica(obs1) and tiene_obs_problematica(obs2):
            pass  # mantener reg1
        else:
            # Ambos tienen dato distinto, marcar conflicto
            mejor["_conflicto_escuela"] = f"{e1} vs {e2}"

    # Observación: limpiar si ya no aplica
    if cambios and tiene_obs_problematica(obs1):
        mejor["observacion"] = ""

    # Página confirmada: preferir la confirmada
    if not reg1.get("pagina_confirmada") and reg2.get("pagina_confirmada"):
        mejor["pagina"] = reg2["pagina"]
        mejor["pagina_confirmada"] = True
        cambios.append(f"pagina: {reg1['pagina']} (hash) -> {reg2['pagina']}")

    return mejor, cambios

def main():
    print("=" * 60)
    print("  CRUCE: PREPRODUCCION vs PTS_CONTROL")
    print("=" * 60)

    # Cargar ambos datasets
    print("\nCargando datos...")
    reg_preprod = cargar_preproduccion()
    print(f"  preproduccion: {len(reg_preprod)} registros")
    reg_control = cargar_pts_control()

    # Indexar por DNI
    idx_preprod = defaultdict(list)
    for r in reg_preprod:
        dni = normalizar_dni(r.get("dni", ""))
        if dni:
            idx_preprod[dni].append(r)

    idx_control = defaultdict(list)
    for r in reg_control:
        dni = normalizar_dni(r.get("dni", ""))
        if dni:
            idx_control[dni].append(r)

    dnis_preprod = set(idx_preprod.keys())
    dnis_control = set(idx_control.keys())

    # Stats
    solo_preprod = dnis_preprod - dnis_control
    solo_control = dnis_control - dnis_preprod
    en_ambos = dnis_preprod & dnis_control

    print(f"\n  DNIs únicos en preproducción: {len(dnis_preprod)}")
    print(f"  DNIs únicos en pts_control:   {len(dnis_control)}")
    print(f"  En ambos (match):             {len(en_ambos)}")
    print(f"  Solo en preproducción:        {len(solo_preprod)}")
    print(f"  Solo en pts_control (nuevos): {len(solo_control)}")

    # Cruzar
    resultado_final = []
    stats = {
        "sin_cambios": 0,
        "mejorados": 0,
        "conflictos_escuela": 0,
        "nuevos_de_control": 0,
        "solo_preprod": 0,
        "paginas_corregidas": 0,
        "nombres_completados": 0,
        "escuelas_completadas": 0,
    }

    # 1. Registros que están en ambos -> merge
    for dni in en_ambos:
        regs_p = idx_preprod[dni]
        regs_c = idx_control[dni]
        # Tomar el primero de cada uno (puede haber duplicados por página)
        base = regs_p[0]
        control = regs_c[0]

        mejor, cambios = elegir_mejor(base, control)

        if cambios:
            stats["mejorados"] += 1
            for c in cambios:
                if "nombre" in c:
                    stats["nombres_completados"] += 1
                if "escuela" in c:
                    stats["escuelas_completadas"] += 1
                if "pagina" in c:
                    stats["paginas_corregidas"] += 1
        else:
            stats["sin_cambios"] += 1

        if "_conflicto_escuela" in mejor:
            stats["conflictos_escuela"] += 1

        mejor["_fuente"] = "cruce"
        resultado_final.append(mejor)

    # 2. Registros solo en preproducción
    for dni in solo_preprod:
        for r in idx_preprod[dni]:
            r["_fuente"] = "preprod"
            resultado_final.append(r)
            stats["solo_preprod"] += 1

    # 3. Registros solo en pts_control (nuevos!)
    for dni in solo_control:
        for r in idx_control[dni]:
            r["_fuente"] = "control"
            resultado_final.append(r)
            stats["nuevos_de_control"] += 1

    # Ordenar por nombre
    resultado_final.sort(key=lambda r: r.get("nombre", ""))

    # Detectar conflictos
    conflictos = [r for r in resultado_final if "_conflicto_escuela" in r]

    # Guardar resultado
    output_path = os.path.join(PREPROD, "padron_cruzado.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_registros": len(resultado_final),
            "stats": stats,
            "registros": resultado_final
        }, f, ensure_ascii=False, indent=2)

    # Guardar conflictos aparte
    if conflictos:
        conflictos_path = os.path.join(PREPROD, "conflictos_escuela.json")
        with open(conflictos_path, "w", encoding="utf-8") as f:
            json.dump(conflictos, f, ensure_ascii=False, indent=2)

    # CSV unificado final
    csv_path = os.path.join(PREPROD, "padron_cruzado.csv")
    if resultado_final:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["TIPO", "DNI", "APELLIDO_NOMBRE", "ESCUELA", "OBSERVACION", "PAGINA", "FUENTE"])
            for r in resultado_final:
                writer.writerow([
                    r.get("tipo", ""),
                    r.get("dni", ""),
                    r.get("nombre", ""),
                    r.get("escuela", ""),
                    r.get("observacion", ""),
                    r.get("pagina", ""),
                    r.get("_fuente", ""),
                ])

    # Resumen
    print(f"\n{'='*60}")
    print(f"  RESULTADO DEL CRUCE")
    print(f"{'='*60}")
    print(f"  Total registros finales:    {len(resultado_final)}")
    print(f"  Match sin cambios:          {stats['sin_cambios']}")
    print(f"  Mejorados por control:      {stats['mejorados']}")
    print(f"    - Nombres completados:    {stats['nombres_completados']}")
    print(f"    - Escuelas completadas:   {stats['escuelas_completadas']}")
    print(f"    - Páginas corregidas:     {stats['paginas_corregidas']}")
    print(f"  Conflictos de escuela:      {stats['conflictos_escuela']}")
    print(f"  Solo en preproducción:      {stats['solo_preprod']}")
    print(f"  Nuevos de pts_control:      {stats['nuevos_de_control']}")
    print(f"\n  Archivos generados:")
    print(f"    {output_path}")
    print(f"    {csv_path}")
    if conflictos:
        print(f"    {os.path.join(PREPROD, 'conflictos_escuela.json')} ({len(conflictos)} conflictos)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
