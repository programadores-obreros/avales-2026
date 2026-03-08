#!/usr/bin/env python3
"""
Procesa una tanda completa de fotos de padrón:
1. Auto-detecta orientación probando 4 rotaciones
2. Detecta número de página via OCR
3. Renombra a pag_XXXX.jpg
4. Ejecuta OCR + post-proceso estructurado

Uso: python3 procesar_tanda.py fotos/Primera_tanda/
"""

import sys
import os
import re
import csv
import json
import subprocess
import shutil
from PIL import Image, ImageOps
import cv2
import numpy as np
import pytesseract

DEFAULT_THRESHOLD = 40
FILAS_ESPERADAS = 60


def corregir_exif(img_path):
    """Corrige orientación EXIF y retorna PIL Image."""
    img = Image.open(img_path)
    img = ImageOps.exif_transpose(img)
    return img


def pil_to_cv(pil_img):
    """Convierte PIL Image a OpenCV BGR."""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def upscale_cv(img_cv, factor=2):
    """Escala imagen x factor."""
    h, w = img_cv.shape[:2]
    return cv2.resize(img_cv, (w * factor, h * factor), interpolation=cv2.INTER_CUBIC)


def preprocess_for_ocr(img_cv, threshold=DEFAULT_THRESHOLD):
    """Preprocesa imagen OpenCV para OCR: gris → normalize → unsharp → threshold."""
    tmp_in = '/tmp/padron_pre_in.png'
    tmp_out = '/tmp/padron_pre_out.png'
    cv2.imwrite(tmp_in, img_cv)
    subprocess.run([
        'magick', tmp_in,
        '-colorspace', 'gray', '-normalize',
        '-unsharp', '6x3+3+0',
        '-threshold', f'{threshold}%',
        '-density', '300',
        tmp_out
    ], capture_output=True)
    result = cv2.imread(tmp_out, cv2.IMREAD_GRAYSCALE)
    for f in [tmp_in, tmp_out]:
        if os.path.exists(f):
            os.remove(f)
    return result


def ocr_text(img_cv, psm=4):
    """OCR sobre imagen OpenCV, retorna texto."""
    config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
    return pytesseract.image_to_string(img_cv, lang='spa', config=config)


def detectar_orientacion_y_pagina(img_path):
    """
    Prueba 4 rotaciones, hace OCR en cada una, busca 'Página XX'.
    Retorna (rotacion_correcta, numero_pagina) o (None, None).
    """
    img = corregir_exif(img_path)
    w, h = img.size

    mejor_rot = None
    mejor_pag = None
    mejor_score = 0

    for rot in [0, 90, 180, 270]:
        rotated = img.rotate(rot, expand=True) if rot > 0 else img
        img_cv = pil_to_cv(rotated)

        # Upscale x2 para mejorar OCR en baja resolución
        img_big = upscale_cv(img_cv, 2)

        # Preprocesar
        processed = preprocess_for_ocr(img_big)
        if processed is None:
            continue

        # OCR completo
        texto = ocr_text(processed)

        # Buscar "Página XXX"
        match = re.search(r'[Pp](?:á|a)gina\s*(\d{1,3})', texto)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 300:
                # Contar cuántos nombres legibles hay (heurística de calidad)
                nombres = len(re.findall(r'[A-ZÁÉÍÓÚÑ]{3,}\s+[A-ZÁÉÍÓÚÑ]{2,}', texto))
                score = nombres
                if score > mejor_score:
                    mejor_rot = rot
                    mejor_pag = num
                    mejor_score = score

    # Si no encontramos página, al menos encontremos la mejor orientación
    if mejor_pag is None:
        for rot in [0, 90, 180, 270]:
            rotated = img.rotate(rot, expand=True) if rot > 0 else img
            img_cv = pil_to_cv(rotated)
            img_big = upscale_cv(img_cv, 2)
            processed = preprocess_for_ocr(img_big)
            if processed is None:
                continue
            texto = ocr_text(processed)
            nombres = len(re.findall(r'[A-ZÁÉÍÓÚÑ]{3,}\s+[A-ZÁÉÍÓÚÑ]{2,}', texto))
            if nombres > mejor_score:
                mejor_rot = rot
                mejor_score = nombres

    return mejor_rot, mejor_pag


def procesar_imagen_completa(img_path, out_dir, pagina_num, rotacion):
    """Procesa una imagen con la rotación correcta."""
    base = f"pag_{pagina_num:04d}"

    img = corregir_exif(img_path)
    if rotacion and rotacion > 0:
        img = img.rotate(rotacion, expand=True)

    img_cv = pil_to_cv(img)
    img_big = upscale_cv(img_cv, 2)

    # Recortar márgenes
    gray = cv2.cvtColor(img_big, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        margin = 20
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(img_big.shape[1] - x, w + 2 * margin)
        h = min(img_big.shape[0] - y, h + 2 * margin)
        img_big = img_big[y:y+h, x:x+w]

    # Preprocesar
    processed = preprocess_for_ocr(img_big)

    # Guardar procesada
    proc_path = os.path.join(out_dir, f"{base}_procesada.png")
    cv2.imwrite(proc_path, processed)

    # OCR
    texto = ocr_text(processed)

    # Guardar OCR raw
    txt_path = os.path.join(out_dir, f"{base}_ocr.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(texto)

    # Parsear registros
    registros = []
    descartadas = []
    for linea in texto.strip().split('\n'):
        reg = parsear_registro(linea)
        if reg and reg['confianza'] >= 30:
            registros.append(reg)
        elif linea.strip() and len(linea.strip()) > 5:
            descartadas.append(linea.strip())

    # CSV
    csv_path = os.path.join(out_dir, f"{base}_datos.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['TIPO', 'DOCUMENTO', 'NOMBRE', 'ESCUELA', 'CONFIANZA'])
        for r in registros:
            writer.writerow([r['tipo'], r['documento'], r['nombre'], r['escuela'], r['confianza']])

    # JSON
    alta = sum(1 for r in registros if r['confianza'] >= 70)
    json_data = {
        'pagina': base,
        'numero': pagina_num,
        'rotacion': rotacion,
        'total_registros': len(registros),
        'filas_esperadas': FILAS_ESPERADAS,
        'completitud': round(len(registros) / FILAS_ESPERADAS * 100),
        'alta_confianza': alta,
        'registros': registros,
        'descartadas': descartadas,
    }
    json_path = os.path.join(out_dir, f"{base}_resultado.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    return json_data


def parsear_registro(linea):
    """Parsea una línea del padrón."""
    linea = linea.strip()
    if not linea or len(linea) < 10:
        return None

    reg = {'tipo': '', 'documento': '', 'nombre': '', 'escuela': '', 'raw': linea, 'confianza': 0}

    dni = re.search(r'\b(\d{7,8})\b', linea)
    if dni:
        reg['documento'] = dni.group(1)
        reg['tipo'] = 'DNI'
        reg['confianza'] += 30

    esc = re.search(r'(0-0\d{2}-[A-Z]{1,2}-\d{4})', linea)
    if esc:
        reg['escuela'] = esc.group(1)
        reg['confianza'] += 30
    elif re.search(r'JUBILADO/?A?', linea, re.IGNORECASE):
        reg['escuela'] = 'JUBILADO/A'
        reg['confianza'] += 25
    elif re.search(r'AP\.?\s*EN\s*SEDE', linea, re.IGNORECASE):
        reg['escuela'] = 'AP. EN SEDE'
        reg['confianza'] += 20

    nombre_m = re.search(r'[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{4,}', linea)
    if nombre_m:
        nombre = nombre_m.group(0).strip()
        nombre = re.sub(r'\b(DNI|LC|JUBILADO/?A?|AP\s*EN\s*SEDE)\b', '', nombre).strip()
        nombre = re.sub(r'\b\d+\b', '', nombre).strip()
        nombre = re.sub(r'\s{2,}', ' ', nombre).strip()
        if len(nombre) > 3:
            reg['nombre'] = nombre
            reg['confianza'] += 40

    return reg if reg['confianza'] >= 30 else None


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 procesar_tanda.py <carpeta_fotos>")
        sys.exit(1)

    carpeta = sys.argv[1]
    if not os.path.isdir(carpeta):
        print(f"Error: '{carpeta}' no es una carpeta")
        sys.exit(1)

    out_dir = 'procesado'
    fotos_dir = 'fotos'
    os.makedirs(out_dir, exist_ok=True)

    imagenes = sorted([
        f for f in os.listdir(carpeta)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    print(f"\n{'='*70}")
    print(f"PROCESANDO TANDA: {carpeta} ({len(imagenes)} imagenes)")
    print(f"Upscale x2 + 4 rotaciones por imagen (esto tarda...)")
    print(f"{'='*70}\n")

    # Paso 1: Detectar orientación y número de página
    print("PASO 1: Detectando orientacion y pagina (4 rotaciones x imagen)...\n")
    paginas = {}
    sin_pagina = []
    orientaciones = {}

    for i, img_name in enumerate(imagenes):
        img_path = os.path.join(carpeta, img_name)
        rot, num = detectar_orientacion_y_pagina(img_path)

        if num is not None:
            if num in paginas:
                print(f"  [{i+1:3d}/{len(imagenes)}] DUPLICADA pag {num}: {img_name}")
            else:
                paginas[num] = img_name
                orientaciones[num] = rot
                print(f"  [{i+1:3d}/{len(imagenes)}] {img_name[:45]} → Pag {num} (rot={rot}°)")
        else:
            sin_pagina.append((img_name, rot))
            print(f"  [{i+1:3d}/{len(imagenes)}] {img_name[:45]} → NO DETECTADA (rot={rot}°)")

    print(f"\n  Detectadas: {len(paginas)}/{len(imagenes)}")
    if sin_pagina:
        print(f"  Sin pagina: {len(sin_pagina)}")

    # Paso 2: Copiar y renombrar
    print(f"\nPASO 2: Renombrando...\n")
    for num in sorted(paginas.keys()):
        src = os.path.join(carpeta, paginas[num])
        dst = os.path.join(fotos_dir, f"pag_{num:04d}.jpg")
        shutil.copy2(src, dst)
        print(f"  pag_{num:04d}.jpg (rot={orientaciones[num]}°) ← {paginas[num][:45]}")

    # Paso 3: OCR completo
    print(f"\nPASO 3: OCR estructurado...\n")
    resultados = []

    for i, num in enumerate(sorted(paginas.keys())):
        img_path = os.path.join(fotos_dir, f"pag_{num:04d}.jpg")
        rot = orientaciones[num]
        print(f"  [{i+1:3d}/{len(paginas)}] pag_{num:04d}...", end=" ", flush=True)

        try:
            resultado = procesar_imagen_completa(img_path, out_dir, num, rot)
            print(f"OK: {resultado['total_registros']} regs ({resultado['completitud']}%), {resultado['alta_confianza']} alta")
            resultados.append(resultado)
        except Exception as e:
            print(f"ERROR: {e}")

    # Resumen
    print(f"\n{'='*70}")
    print(f"RESUMEN FINAL")
    print(f"{'='*70}\n")

    if resultados:
        total_regs = sum(r['total_registros'] for r in resultados)
        total_alta = sum(r['alta_confianza'] for r in resultados)
        avg_comp = round(sum(r['completitud'] for r in resultados) / len(resultados))

        print(f"  Paginas procesadas:   {len(resultados)}")
        print(f"  Total registros:      {total_regs}")
        print(f"  Alta confianza:       {total_alta}")
        print(f"  Completitud promedio: {avg_comp}%")

        print(f"\n  {'PAG':>6} {'REGS':>6} {'COMP':>6} {'ALTA':>6} {'ROT':>5}")
        print(f"  {'-'*35}")
        for r in sorted(resultados, key=lambda x: x['numero']):
            marca = '  ' if r['completitud'] >= 80 else ' !' if r['completitud'] >= 50 else '!!'
            print(f"  {r['numero']:>6} {r['total_registros']:>6} {r['completitud']:>5}% {r['alta_confianza']:>6} {r['rotacion']:>4}° {marca}")

    if sin_pagina:
        print(f"\n  FOTOS SIN PAGINA ({len(sin_pagina)}):")
        for sp, rot in sin_pagina:
            print(f"    - {sp} (rot={rot}°)")

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
