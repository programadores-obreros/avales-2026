#!/usr/bin/env python3
"""Parsea el texto OCR crudo de una pagina del boletin CTERA a registros MESA.

No hardcodea encabezados de seccion/sindicato (varian por pagina/provincia,
son decenas distintos a lo largo del pais). En cambio usa cada aparicion de
"MESA 1" como limite de un dominio de numeracion local: SUTEBA Buenos Aires,
por ejemplo, tiene ~130 localidades que TODAS reinician su propia "MESA 1,
MESA 2, MESA 3...", mientras que otros sindicatos (ej. SUTE Mendoza) numeran
sus mesas de forma continua para toda la provincia (una sola "MESA 1" en
toda la seccion). El chequeo de duplicados debe respetar esos limites o
genera falsos positivos masivos (~70% en paginas con muchas localidades).

Uso: parse_page.py out_pageNN_full.txt <numero_pagina> > pageNN_mesas.json
"""
import sys, re, json
from collections import defaultdict

MESA_RE = re.compile(r'MESA[^\d]{0,4}(\d{1,3})\b')

def parse(path, page_num):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    text = " ".join(l.strip() for l in raw.splitlines() if l.strip())
    text = re.sub(r"\s+", " ", text)

    splits = list(MESA_RE.finditer(text))

    # limites de dominio: cada match cuyo numero es "1" empieza un dominio nuevo
    # (si la pagina no empieza con MESA 1, el primer tramo es dominio 0 = posible
    # continuacion de la pagina anterior, sin limite conocido)
    domain_id = 0
    domain_starts = {0: 0}  # indice en `splits` donde empieza cada dominio
    for idx, m in enumerate(splits):
        if idx == 0:
            continue
        if m.group(1) == "1":
            domain_id += 1
            domain_starts[domain_id] = idx

    # mapear cada indice de split a su dominio
    domain_boundaries = sorted(domain_starts.items(), key=lambda kv: kv[1])
    def domain_for_index(idx):
        d = 0
        for did, start_idx in domain_boundaries:
            if idx >= start_idx:
                d = did
            else:
                break
        return d

    records = []
    for j, m in enumerate(splits):
        mesa_num = m.group(1)
        seg_start = m.end()
        seg_end = splits[j + 1].start() if j + 1 < len(splits) else len(text)
        cuerpo = text[seg_start:seg_end].strip(" :.,;-")
        matched_raw = m.group(0)
        dom = domain_for_index(j)

        # etiqueta best-effort de la localidad: texto entre el fin de la mesa
        # anterior (de otro dominio) y el inicio de este match, si este es el
        # primer registro del dominio
        etiqueta = None
        if j == domain_starts.get(dom):
            prev_end = splits[j - 1].end() if j > 0 else 0
            # el cuerpo del registro anterior ya incluye el texto hasta aca;
            # tomamos los ultimos ~80 chars antes de este match como pista,
            # buscando desde el propio texto crudo (no el cuerpo ya cortado)
            candidate = text[max(0, m.start() - 80):m.start()]
            # nos quedamos con el ultimo fragmento separable por coma/punto
            candidate = re.split(r'[.,;]', candidate)[-1].strip()
            if candidate and len(candidate) < 60:
                etiqueta = candidate

        rec = {
            "page": page_num,
            "dominio": dom,
            "dominio_etiqueta": etiqueta,
            "mesa": mesa_num,
            "match_crudo": matched_raw,
            "texto": cuerpo[:500],
        }
        if not re.fullmatch(r'MESA\s*N?[°ºo\"\'\?]{0,2}\s*\d{1,3}', matched_raw, flags=re.IGNORECASE):
            rec["incierto"] = True
        records.append(rec)

    # QA de duplicados AHORA ACOTADO por dominio (localidad/seccion), no por pagina completa
    counts = defaultdict(int)
    for r in records:
        counts[(r["dominio"], r["mesa"])] += 1
    for r in records:
        if counts[(r["dominio"], r["mesa"])] > 1:
            r["sospechoso_duplicado"] = True

    n_incierto = sum(1 for r in records if r.get("incierto"))
    n_dup = sum(1 for r in records if r.get("sospechoso_duplicado"))
    n_dominios = len(set(r["dominio"] for r in records))

    return {
        "page": page_num,
        "total_mesas_detectadas": len(records),
        "dominios_detectados": n_dominios,
        "marcadas_inciertas_formato": n_incierto,
        "marcadas_sospechosas_duplicado": n_dup,
        "records": records,
    }

if __name__ == "__main__":
    path = sys.argv[1]
    page_num = int(sys.argv[2])
    print(json.dumps(parse(path, page_num), ensure_ascii=False, indent=2))
