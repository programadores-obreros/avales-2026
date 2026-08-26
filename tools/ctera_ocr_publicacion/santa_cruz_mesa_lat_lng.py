#!/usr/bin/env python3
"""Genera la tabla mesa -> {mesa_sede, mesa_direccion, mesa_lat, mesa_lng}
para ADOSAC (Santa Cruz), a partir de santa_cruz_geocoded.json.

Las 16 mesas reales de ADOSAC.pdf son 1A,1B,2A,2B,3..14 (Rio Gallegos y
Caleta Olivia se desdoblan en 2 mesas cada uno, comparten sede/coords).
El campo "mesa" en Firestore para ADOSAC viene de MESA_RE en
consolidar_padron_ctera.py: r"MESA\\s*...(\\d+[A-Za-z]?)" -> "1A","1B", etc,
coincide exacto con las claves de este diccionario (no hace falta normalizar).

Uso: python3 santa_cruz_mesa_lat_lng.py > santa_cruz_mesa_lat_lng.json
Consumido despues por import-firestore.mjs en ctera-2026 (paso separado,
no incluido aca -- esto solo prepara la tabla, no toca Firestore).
"""
import json

# sede + direccion EXACTOS tal como los guarda mesa_sede_pdf en el
# consolidador (sindicato=ADOSAC): f"{sede_nombre} - {direccion}"
GEOCODED = json.load(open("/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/ctera/consolidado/santa_cruz_geocoded.json"))

# mapa localidad (del geocoded) -> lista de mesas reales de ADOSAC que
# comparten esa sede (Rio Gallegos = 1A+1B, Caleta Olivia = 2A+2B, resto 1 a 1)
MESAS_POR_LOCALIDAD = {
    "Río Gallegos": ["1A", "1B"],
    "Caleta Olivia": ["2A", "2B"],
    "Perito Moreno": ["3"],
    "Las Heras": ["4"],
    "Pico Truncado": ["5"],
    "Puerto Deseado": ["6"],
    "Pto. San Julián": ["7"],
    "Gobernador Gregores": ["8"],
    "Piedra Buena": ["9"],
    "Puerto Santa Cruz": ["10"],
    "El Calafate": ["11"],
    "Río Turbio": ["12"],
    "28 de Noviembre": ["13"],
    "Los Antiguos": ["14"],
}

SEDE_POR_LOCALIDAD = {
    "Río Gallegos": "FILIAL RIO GALLEGOS",
    "Caleta Olivia": "FILIAL CALETA OLIVIA",
    "Perito Moreno": "FILIAL PERITO MORENO",
    "Las Heras": "FILIAL LAS HERAS",
    "Pico Truncado": "FILIAL PICO TRUNCADO",
    "Puerto Deseado": "FILIAL PUERTO DESEADO",
    "Pto. San Julián": "FILIAL PTO. SAN JULIAN",
    "Gobernador Gregores": "FILIAL GOBERNADOR GREGORES",
    "Piedra Buena": "FILIAL PIEDRA BUENA",
    "Puerto Santa Cruz": "FILIAL PUERTO SANTA CRUZ",
    "El Calafate": "FILIAL EL CALAFATE",
    "Río Turbio": "FILIAL RIO TURBIO",
    "28 de Noviembre": "FILIAL 28 DE NOVIEMBRE",
    "Los Antiguos": "FILIAL LOS ANTIGUOS",
}

por_localidad = {r["localidad"]: r for r in GEOCODED}

tabla = {}
for localidad, mesas in MESAS_POR_LOCALIDAD.items():
    g = por_localidad[localidad]
    for mesa in mesas:
        tabla[mesa] = {
            "mesa_sede": SEDE_POR_LOCALIDAD[localidad],
            "mesa_direccion": g["direccion"],
            "mesa_lat": g["lat"],
            "mesa_lng": g["lon"],
            "mesa_nota": (
                "Ubicación aproximada al centro de la localidad, no a la dirección exacta"
                if "aproximado" in g["status"] else None
            ),
            "_fuente_status": g["status"],
        }

print(json.dumps(tabla, ensure_ascii=False, indent=2))
