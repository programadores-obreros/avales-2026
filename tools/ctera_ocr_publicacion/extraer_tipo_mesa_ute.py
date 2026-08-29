#!/usr/bin/env python3
"""Extrae el tipo de mesa (Fija / Volante) de UTE (CABA) desde el Excel que
pasó el usuario, y lo cruza contra el número de mesa real del padrón.

Fuente: ctera/CABA/Mesas_UTE-CTERA_con tipo_volantes.xlsx (columna "Nro" =
número de mesa real, validado 1:1 contra las 136 mesas del padrón
consolidado — 0 faltantes, 0 duplicados, 2026-08-29).

Una mesa "Volante" agrupa afiliados/as sin lugar de trabajo fijo — la
dirección que tenemos geocodificada es la sede designada, pero puede
confirmarse/cambiar más cerca de la fecha (confirmado por el usuario,
no es una inferencia). Por eso se marca aparte del resto, para mostrar
una advertencia clara en el sitio en vez de tratarla como una mesa fija.
"""
import json

import openpyxl

XLSX_PATH = "/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/ctera/CABA/Mesas_UTE-CTERA_con tipo_volantes.xlsx"
OUT_PATH = "/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/ctera/consolidado/ute_caba_mesa_tipo.json"

wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
ws = wb["Datos Mesas"]

resultados = []
for row in ws.iter_rows(min_row=2, values_only=True):
    nro, tipo = row[0], row[1]
    if nro is None or tipo is None:
        continue
    resultados.append({"mesa": str(nro), "tipo": tipo})

resultados.sort(key=lambda r: int(r["mesa"]))

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

from collections import Counter

conteo = Counter(r["tipo"] for r in resultados)
print(f"Total mesas: {len(resultados)}")
print(f"Por tipo: {dict(conteo)}")
print(f"Escrito en: {OUT_PATH}")
