#!/usr/bin/env python3
"""Geocodifica las 186 mesas de UEPC (Córdoba) via Nominatim (OSM).
Mismo patron que geocode_ute_caba.py / geocode_santa_cruz.py. Direccion
limpia del propio PDF oficial (texto seleccionable), extraida por
UEPC_HEADER_RE en consolidar_padron_ctera.py (auditoria 2026-08-25).
mesa_sede_pdf = "{sede} - {direccion, localidad}".
"""
import json
import time
import requests

HEADERS = {"User-Agent": "eleccionesSUTEBA2026-geocode/1.0 (uso interno, sin fines comerciales)"}
URL = "https://nominatim.openstreetmap.org/search"

with open("/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/ctera/consolidado/padron_ctera_2026_dedup.json", encoding="utf-8") as f:
    data = json.load(f)

uepc = [r for r in data if r.get("sindicato") == "UEPC"]
mesas = {}
for r in uepc:
    key = (r.get("archivo_origen"), r.get("mesa"))
    if key not in mesas:
        mesas[key] = r.get("mesa_sede_pdf", "")

def split_sede_direccion(texto):
    if " - " in texto:
        sede, direccion = texto.split(" - ", 1)
        return sede.strip(), direccion.strip()
    return texto.strip(), ""

def geocode(query):
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "ar"}
    r = requests.get(URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    d = r.json()
    if d:
        return float(d[0]["lat"]), float(d[0]["lon"]), d[0].get("display_name")
    return None, None, None

resultados = []
for i, ((archivo, mesa), texto) in enumerate(sorted(mesas.items())):
    sede, direccion = split_sede_direccion(texto)
    if not direccion:
        # No se pudo separar sede/direccion con confianza (formatos con
        # puntos/guiones sueltos, ambiguos de partir sin arriesgar un corte
        # incorrecto -- 39/186 casos, auditoria 2026-08-25). En vez de
        # perder el dato, se geocodifica el texto COMPLETO tal cual viene:
        # Nominatim en la practica ignora bien palabras como "Escuela" o
        # "IPEM 179" y matchea igual contra la calle+numero+localidad real.
        query = f"{texto}, Córdoba, Argentina"
        lat, lon, display = geocode(query)
        status = "ok_texto_completo" if lat else "sin_resultado"
        resultados.append({"archivo_origen": archivo, "mesa": mesa, "sede": sede or texto,
                            "direccion": None, "lat": lat, "lon": lon,
                            "display_name": display, "status": status})
        print(f"[{i+1}/186] {archivo:<45} mesa={mesa:<3} (texto completo) {texto[:35]:<35} -> {status}")
        time.sleep(1)
        continue
    query = f"{direccion}, Córdoba, Argentina"
    lat, lon, display = geocode(query)
    status = "ok" if lat else "sin_resultado"
    # clave = archivo_origen, NO mesa: 22 numeros de mesa se repiten entre
    # departamentos distintos (ej. "Mesa 3" aparece en 18 archivos), un
    # indice por numero de mesa solo (como UTE/ADOSAC) pisaria resultados
    # entre si. Verificado 2026-08-25 antes de escribir esto.
    resultados.append({"archivo_origen": archivo, "mesa": mesa, "sede": sede,
                        "direccion": direccion, "lat": lat, "lon": lon,
                        "display_name": display, "status": status})
    print(f"[{i+1}/186] {archivo:<45} mesa={mesa:<3} {direccion:<40} -> {status}")
    time.sleep(1)

with open("/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/ctera/consolidado/uepc_cordoba_geocoded.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

ok = sum(1 for r in resultados if r["status"] == "ok")
ok_texto = sum(1 for r in resultados if r["status"] == "ok_texto_completo")
fail = sum(1 for r in resultados if r["status"] == "sin_resultado")
print()
print(f"Exactas (direccion limpia): {ok}/{len(resultados)}")
print(f"Exactas (texto completo, fallback): {ok_texto}/{len(resultados)}")
print(f"Total con coordenadas: {ok+ok_texto}/{len(resultados)}")
print(f"Sin resultado: {fail}/{len(resultados)}")
