#!/usr/bin/env python3
"""
Extrae las mesas de votación del PDF de elecciones SUTEBA 2026.
Genera un CSV estructurado con: localidad, mesa, tipo, numero, direccion.
"""
import fitz
import re
import csv
from collections import Counter

PDF_PATH = "/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/13_mayo_2026/2026-el-13-de-mayo-de-2026-votamos-lxs-docentes-en-toda-la-provincia-de-buenos-aires-113943.pdf"
OUTPUT_CSV = "/home/manjarodesktop/2025/po/eleccionesSUTEBA2026/13_mayo_2026/mesas_suteba_2026.csv"

# Códigos de tipo de ubicación encontrados en el PDF
# Sede = Sede seccional, MS = Mesa Sindical, PP/EE/JI/IS/MT/SC/DF/MA/EL/DM = establecimientos
# Códigos adicionales: AA, AM, AS, AT, AV, AZ, CFP, DE, FC, IC, J, JM, JS, M, MC, MM, OR, P, PA, TH, TJO
KNOWN_TYPES = {
    'Sede', 'MS', 'PP', 'MT', 'SC', 'EE', 'AE', 'JI', 'DF', 'IS', 'MA', 'EL', 'DM',
    'AA', 'AM', 'AS', 'AT', 'AV', 'AZ', 'CFP', 'DE', 'FC', 'IC', 'J', 'JM', 'JS',
    'M', 'MC', 'MM', 'OR', 'P', 'PA', 'TH', 'TJO',
}
# Tipos sin número (como Sede)
NO_NUM_TYPES = {'Sede', 'TJO'}
# Regex para matchear tipo + número o tipo solo
# Ordenar por longitud descendente para que CFP matchee antes que C, TJO antes que T, etc.
WITH_NUM_TYPES = '|'.join(sorted((c for c in KNOWN_TYPES if c not in NO_NUM_TYPES), key=len, reverse=True))
NO_NUM_ALTS = '|'.join(sorted(NO_NUM_TYPES, key=len, reverse=True))
TYPE_PATTERN = re.compile(
    rf'^((?:{NO_NUM_ALTS})|(?:{WITH_NUM_TYPES})\s+\d+)'
)


def extract_spans(pdf_path):
    """Extrae todos los spans de tamaño ~8pt con info de fuente y posición."""
    doc = fitz.open(pdf_path)
    all_spans = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_width = page.rect.width
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    size = span["size"]
                    text = span["text"].strip()
                    if not text or abs(size - 8.0) >= 0.5:
                        continue

                    bbox = span["bbox"]
                    is_bold = "Hv" in span["font"]
                    col = 0 if bbox[0] < page_width / 2 else 1

                    all_spans.append({
                        "text": text,
                        "is_bold": is_bold,
                        "page": page_num,
                        "col": col,
                        "y": round(bbox[1], 1),
                        "x": round(bbox[0], 1),
                    })

    doc.close()

    # Ordenar: página → columna → Y → X (orden de lectura)
    all_spans.sort(key=lambda s: (s["page"], s["col"], s["y"], s["x"]))
    return all_spans


def build_localities(spans):
    """Agrupa spans en localidades con su texto de mesas."""
    localities = []
    current_locality = None
    text_parts = []

    for span in spans:
        if span["is_bold"]:
            if current_locality is not None:
                if not text_parts:
                    # Consecutivos en negrita sin texto entre ellos → mergear
                    # (nombre de localidad partido por salto de línea en el PDF)
                    current_locality += " " + span["text"]
                else:
                    # Había texto regular → guardar localidad anterior y empezar nueva
                    localities.append((current_locality, " ".join(text_parts)))
                    current_locality = span["text"]
                    text_parts = []
            else:
                current_locality = span["text"]
        else:
            text_parts.append(span["text"])

    # Última localidad
    if current_locality is not None:
        localities.append((current_locality, " ".join(text_parts)))

    return localities


def split_embedded_localities(localities):
    """Detecta localidades embebidas por reinicio de numeración de mesas (M1 duplicado).

    Esto ocurre cuando el PDF no pone en negrita un nombre de localidad (ej: LA PLATA).
    Se detecta buscando un segundo 'M1' en el texto y extrayendo el nombre en MAYÚSCULAS
    que lo precede.
    """
    result = []

    for loc_name, text in localities:
        # Buscar todas las posiciones de M1 (con word boundary)
        m1_positions = [m.start() for m in re.finditer(r'\bM1\b', text)]

        if len(m1_positions) <= 1:
            result.append((loc_name, text))
            continue

        # Hay más de un M1 → localidad embebida
        # Separar en el segundo M1
        split_pos = m1_positions[1]
        before = text[:split_pos].rstrip()
        after = text[split_pos:]

        # Extraer nombre de localidad del final del texto anterior
        # Patrón: PALABRAS EN MAYÚSCULAS al final, precedidas por un número (dirección)
        name_match = re.search(
            r'(?<=\d\s)([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ.\s]{1,40}?)\s*$',
            before,
        )

        if name_match:
            embedded_name = name_match.group(1).strip()
            first_text = before[:name_match.start()].strip()
            result.append((loc_name, first_text))
            result.append((embedded_name, after))
        else:
            # No se pudo detectar el nombre → dejar como está y avisar
            result.append((loc_name, text))

    return result


def parse_mesas(text):
    """Parsea las mesas de una localidad desde su texto continuo."""
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []

    # Limpiar artefactos del PDF
    text = text.replace('°', '').replace('º', '')  # quitar símbolos grado corruptos
    text = re.sub(r'\s+', ' ', text).strip()  # renormalizar espacios

    # Separar por tokens M\d+ manteniendo los delimitadores
    parts = re.split(r'(\bM\d+\b)', text)

    results = []
    current_mesas = []  # grupo de mesas que comparten ubicación

    i = 1  # parts[0] es texto antes del primer M (lo ignoramos)
    while i < len(parts):
        mesa_token = parts[i]
        mesa_num = int(re.search(r'\d+', mesa_token).group())
        current_mesas.append(mesa_num)

        # Texto después de este token M\d+
        after = parts[i + 1].strip() if i + 1 < len(parts) else ""

        if not after or after in ('y', 'e'):
            # Vacío o conjunción → siguiente M\d+ comparte ubicación (mismo grupo)
            i += 2
            continue

        # Intentar matchear un código de tipo
        m = TYPE_PATTERN.match(after)

        if m:
            tipo_raw = m.group(1).strip()
            address = after[m.end():].strip().strip(',').strip()

            # Separar código y número
            tipo_parts = tipo_raw.split(None, 1)
            tipo = tipo_parts[0]
            numero = tipo_parts[1] if len(tipo_parts) > 1 else ""

            for mesa in current_mesas:
                results.append({
                    "mesa": f"M{mesa}",
                    "tipo": tipo,
                    "numero": numero,
                    "direccion": address,
                })
            current_mesas = []
        else:
            # No es un tipo conocido → ubicación descriptiva (sin código estándar)
            for mesa in current_mesas:
                results.append({
                    "mesa": f"M{mesa}",
                    "tipo": "OTRO",
                    "numero": "",
                    "direccion": after,
                })
            current_mesas = []

        i += 2

    # Mesas huérfanas al final del texto (sin tipo asignado)
    for mesa in current_mesas:
        results.append({
            "mesa": f"M{mesa}",
            "tipo": "OTRO",
            "numero": "",
            "direccion": "",
        })

    return results


def main():
    print("Extrayendo spans del PDF...")
    spans = extract_spans(PDF_PATH)
    print(f"  → {len(spans)} spans extraídos")

    print("Construyendo localidades...")
    localities = build_localities(spans)
    print(f"  → {len(localities)} localidades (por negrita)")

    # Detectar localidades embebidas (no en negrita, como LA PLATA)
    localities = split_embedded_localities(localities)
    print(f"  → {len(localities)} localidades (post-split por reinicio M1)")

    print("Parseando mesas...")
    all_records = []
    issues = []

    for localidad, mesa_text in localities:
        mesas = parse_mesas(mesa_text)
        for mesa in mesas:
            record = {"localidad": localidad, **mesa}
            all_records.append(record)
            if mesa["tipo"] == "OTRO":
                issues.append(f"  {localidad} {mesa['mesa']}: {mesa['direccion'][:60]}")

    print(f"  → {len(all_records)} mesas totales extraídas")

    # Warnings
    if issues:
        print(f"\nℹ {len(issues)} entradas con ubicación descriptiva (tipo=OTRO):")
        for issue in issues[:15]:
            print(issue)
        if len(issues) > 15:
            print(f"  ... y {len(issues) - 15} más")

    # Escribir CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["localidad", "mesa", "tipo", "numero", "direccion"]
        )
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nCSV guardado en: {OUTPUT_CSV}")

    # Stats
    loc_counts = Counter(r["localidad"] for r in all_records)
    type_counts = Counter(r["tipo"] for r in all_records)

    print(f"\n--- Estadísticas ---")
    print(f"Localidades: {len(loc_counts)}")
    print(f"Mesas totales: {len(all_records)}")
    print(f"\nTipos de ubicación:")
    for tipo, count in type_counts.most_common():
        print(f"  {tipo}: {count}")
    print(f"\nTop 10 localidades por cantidad de mesas:")
    for loc, count in loc_counts.most_common(10):
        print(f"  {loc}: {count}")

    # Muestra primeras 15 filas
    print(f"\n--- Primeras 15 filas ---")
    for r in all_records[:15]:
        print(f"  {r['localidad']:25s} | {r['mesa']:4s} | {r['tipo']:6s} {r['numero']:4s} | {r['direccion']}")


if __name__ == "__main__":
    main()
