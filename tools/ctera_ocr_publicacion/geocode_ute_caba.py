#!/usr/bin/env python3
"""Geocodifica las sedes de UTE (Ciudad Autónoma de Buenos Aires) via
Nominatim (OSM). Mismo patrón que geocode_santa_cruz.py: 1 req/seg,
User-Agent custom, sin API key.

Fuente de las sedes: padron_ctera_2026_dedup.json (mesa_sede_pdf), volcado
previamente a ute_sedes_a_geocodificar.json.
"""
import json
import re
import time

import requests

SEDES_PATH = "/tmp/claude-1000/-home-manjarodesktop-2025-po-eleccionesSUTEBA2026/f5eca6c1-5f57-48e8-a165-fe26c3711f19/scratchpad/ute_sedes_a_geocodificar.json"
OUT_PATH = "../../ctera/consolidado/ute_caba_geocoded.json"

HEADERS = {"User-Agent": "eleccionesSUTEBA2026-geocode/1.0 (uso interno, sin fines comerciales)"}
URL = "https://nominatim.openstreetmap.org/search"


def limpiar_direccion(direccion):
    # OCR del PDF a veces pega la calle con el número ("Libertad1257").
    # Separar solo cuando una letra queda pegada directo a un dígito.
    return re.sub(r"([a-zA-Záéíóúñ])(\d)", r"\1 \2", direccion)


def geocode(query):
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "ar"}
    r = requests.get(URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name")
    return None, None, None


with open(SEDES_PATH, encoding="utf-8") as f:
    sedes = json.load(f)

results = []
for s in sedes:
    direccion = limpiar_direccion(s["direccion"])
    query = f"{direccion}, Ciudad Autónoma de Buenos Aires, Argentina"
    lat, lon, display = geocode(query)
    status = "ok" if lat else "sin_resultado"
    if not lat:
        # fallback: sede + CABA, sin número de calle exacto
        query2 = f"{s['sede']}, Ciudad Autónoma de Buenos Aires, Argentina"
        time.sleep(1)
        lat, lon, display = geocode(query2)
        status = "aproximado_por_sede" if lat else "sin_resultado"
    results.append({**s, "direccion_limpia": direccion, "query": query, "lat": lat, "lon": lon, "display_name": display, "status": status})
    print(f"mesa {s['mesa']:5s} {s['sede'][:30]:30s} -> {status:22s} {lat},{lon}")
    time.sleep(1)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

ok = sum(1 for r in results if r["status"] == "ok")
aprox = sum(1 for r in results if r["status"] == "aproximado_por_sede")
fail = sum(1 for r in results if r["status"] == "sin_resultado")
print()
print(f"Exactas: {ok}/{len(results)}, Aproximadas (solo sede): {aprox}/{len(results)}, Sin resultado: {fail}/{len(results)}")
