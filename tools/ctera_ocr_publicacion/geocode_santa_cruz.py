#!/usr/bin/env python3
"""Geocodifica las 14 mesas de ADOSAC (Santa Cruz) via Nominatim (OSM).
Patron ya usado en el proyecto: tmp/circuito_documentacion.md sec. 4.1.
1 req/seg, User-Agent custom, sin API key.
"""
import time
import json
import requests

MESAS = [
    {"mesa": "1A/1B", "localidad": "Río Gallegos", "direccion": "Pasteur 813"},
    {"mesa": "2A/2B", "localidad": "Caleta Olivia", "direccion": "Av. Eva Perón 384"},
    {"mesa": "3", "localidad": "Perito Moreno", "direccion": "Padre Giori 1080"},
    {"mesa": "4", "localidad": "Las Heras", "direccion": "San Martín 946"},
    {"mesa": "5", "localidad": "Pico Truncado", "direccion": "Urquiza 115"},
    {"mesa": "6", "localidad": "Puerto Deseado", "direccion": "Almirante Brown 1531"},
    {"mesa": "7", "localidad": "Pto. San Julián", "direccion": "Piedra Buena y Brown"},
    {"mesa": "8", "localidad": "Gobernador Gregores", "direccion": "Barrenechea 655"},
    {"mesa": "9", "localidad": "Piedra Buena", "direccion": "Cipriano García Norte 658"},
    {"mesa": "10", "localidad": "Puerto Santa Cruz", "direccion": "San Juan Bosco 960"},
    {"mesa": "11", "localidad": "El Calafate", "direccion": "Cte. Tola 315"},
    {"mesa": "12", "localidad": "Río Turbio", "direccion": "Oneto 101"},
    {"mesa": "13", "localidad": "28 de Noviembre", "direccion": "San Martín 845"},
    {"mesa": "14", "localidad": "Los Antiguos", "direccion": "Casiano Bulgarin S/N"},
]

HEADERS = {"User-Agent": "eleccionesSUTEBA2026-geocode/1.0 (uso interno, sin fines comerciales)"}
URL = "https://nominatim.openstreetmap.org/search"

def geocode(query):
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "ar"}
    r = requests.get(URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name")
    return None, None, None

results = []
for m in MESAS:
    query = f"{m['direccion']}, {m['localidad']}, Santa Cruz, Argentina"
    lat, lon, display = geocode(query)
    status = "ok" if lat else "sin_resultado"
    if not lat:
        # fallback: solo localidad (sin numero de calle exacto), mejor que nada
        query2 = f"{m['localidad']}, Santa Cruz, Argentina"
        lat, lon, display = geocode(query2)
        status = "aproximado_solo_localidad" if lat else "sin_resultado"
        time.sleep(1)
    results.append({**m, "query": query, "lat": lat, "lon": lon, "display_name": display, "status": status})
    print(f"{m['mesa']:8s} {m['localidad']:20s} -> {status:28s} {lat},{lon}")
    time.sleep(1)

with open("santa_cruz_geocoded.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

ok = sum(1 for r in results if r["status"] == "ok")
aprox = sum(1 for r in results if r["status"] == "aproximado_solo_localidad")
fail = sum(1 for r in results if r["status"] == "sin_resultado")
print()
print(f"Exactas: {ok}/14, Aproximadas (solo localidad): {aprox}/14, Sin resultado: {fail}/14")
