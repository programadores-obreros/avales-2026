#!/usr/bin/env python3
"""
Pipeline de preprocesamiento + OCR + post-proceso para padrones SUTEBA.

Uso:
  python3 procesar_padron.py fotos/pag_0162.jpg
  python3 procesar_padron.py fotos/pag_0162.jpg --thresh 42

Estructura de cada hoja (~60 filas):
  TIPO | DOCUMENTO | APELLIDO NOMBRE | ESCUELA
  DNI  | 27241872  | VILLAFAÑE JORGE  | 0-069-MT-0001
  DNI  | 17257008  | ZARATE SONIA     | JUBILADO/A
"""

import sys
import os
import re
import csv
import subprocess
import json
import cv2
import numpy as np
from PIL import Image, ImageOps
import pytesseract


DEFAULT_THRESHOLD = 40

# Códigos de escuela conocidos
CODIGOS_ESCUELA = {'DF', 'DM', 'EE', 'FP', 'J', 'MS', 'MT', 'PP', 'AA', 'JH',
                   'RC', 'SC', 'DC', 'DP', 'IS', 'TI', 'TM'}

FILAS_ESPERADAS = 60


def corregir_exif(img_path):
    """Corrige orientación EXIF y retorna imagen OpenCV."""
    pil_img = Image.open(img_path)
    pil_img = ImageOps.exif_transpose(pil_img)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def detectar_y_recortar_tabla(img):
    """Detecta el área de la tabla y recorta, eliminando márgenes."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binarizar para detectar contenido
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Encontrar contornos del contenido
    coords = cv2.findNonZero(binary)
    if coords is None:
        return img

    x, y, w, h = cv2.boundingRect(coords)

    # Agregar un poco de margen
    margin = 20
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(img.shape[1] - x, w + 2 * margin)
    h = min(img.shape[0] - y, h + 2 * margin)

    cropped = img[y:y+h, x:x+w]
    return cropped


def enderezar(img):
    """Corrige la inclinación de la imagen."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(binary > 0))
    if len(coords) < 500:
        return img

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Solo corregir inclinaciones menores a 10 grados
    if abs(angle) > 10 or abs(angle) < 0.2:
        return img

    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    print(f"     Enderezado: {angle:.2f} grados")
    return rotated


def preprocesar_imagen(img_path, threshold=DEFAULT_THRESHOLD):
    """Pipeline completo: EXIF → recortar → enderezar → ImageMagick."""
    print(f"  1. Corrigiendo EXIF...")
    img = corregir_exif(img_path)
    print(f"     Dimensiones: {img.shape[1]}x{img.shape[0]}")

    print(f"  2. Recortando tabla...")
    cropped = detectar_y_recortar_tabla(img)
    print(f"     Recortado: {cropped.shape[1]}x{cropped.shape[0]}")

    print(f"  3. Enderezando...")
    straight = enderezar(cropped)

    # Guardar temporal para ImageMagick
    tmp_path = '/tmp/padron_tmp_crop.png'
    cv2.imwrite(tmp_path, straight)

    # ImageMagick: normalize + unsharp + threshold
    out_path = '/tmp/padron_tmp_final.png'
    print(f"  4. Preprocesando (normalize + unsharp + threshold {threshold}%)...")
    subprocess.run([
        'magick', tmp_path,
        '-colorspace', 'gray',
        '-normalize',
        '-unsharp', '6x3+3+0',
        '-threshold', f'{threshold}%',
        '-density', '300',
        out_path
    ], check=True, capture_output=True)

    os.remove(tmp_path)
    return out_path, straight


def hacer_ocr(img_path):
    """Ejecuta OCR optimizado para tablas."""
    config = '--oem 3 --psm 4 -c preserve_interword_spaces=1'
    texto = pytesseract.image_to_string(img_path, lang='spa', config=config)
    return texto


def parsear_linea(linea):
    """Intenta parsear una línea del padrón a la estructura conocida."""
    linea = linea.strip()
    if not linea or len(linea) < 10:
        return None

    resultado = {
        'tipo': '',
        'documento': '',
        'nombre': '',
        'escuela': '',
        'raw': linea,
        'confianza': 0,
    }

    # Intentar extraer DNI (7-8 dígitos)
    dni_match = re.search(r'\b(\d{7,8})\b', linea)
    if dni_match:
        resultado['documento'] = dni_match.group(1)
        resultado['tipo'] = 'DNI'
        resultado['confianza'] += 30

    # Intentar extraer código de escuela: 0-069-XX-XXXX o 0-0XX-XX-XXXX
    escuela_match = re.search(r'(0-0\d{2}-[A-Z]{1,2}-\d{4})', linea)
    if escuela_match:
        resultado['escuela'] = escuela_match.group(1)
        resultado['confianza'] += 30
    elif re.search(r'JUBILADO/?A?', linea, re.IGNORECASE):
        resultado['escuela'] = 'JUBILADO/A'
        resultado['confianza'] += 25
    elif re.search(r'AP\.?\s*EN\s*SEDE', linea, re.IGNORECASE):
        resultado['escuela'] = 'AP. EN SEDE'
        resultado['confianza'] += 20

    # Intentar extraer nombre (texto en mayúsculas entre DNI y código)
    nombre_match = re.search(r'[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{4,}', linea)
    if nombre_match:
        nombre = nombre_match.group(0).strip()
        # Limpiar: quitar DNI, código, y palabras sueltas del inicio
        nombre = re.sub(r'\b(DNI|JUBILADO/?A?|AP\s*EN\s*SEDE)\b', '', nombre).strip()
        nombre = re.sub(r'\b\d+\b', '', nombre).strip()
        nombre = re.sub(r'\s{2,}', ' ', nombre).strip()
        if len(nombre) > 3:
            resultado['nombre'] = nombre
            resultado['confianza'] += 40

    return resultado if resultado['confianza'] > 0 else None


def postprocesar(texto_ocr):
    """Parsea el texto OCR completo a registros estructurados."""
    lineas = texto_ocr.strip().split('\n')
    registros = []
    descartadas = []

    for linea in lineas:
        registro = parsear_linea(linea)
        if registro and registro['confianza'] >= 30:
            registros.append(registro)
        elif linea.strip():
            descartadas.append(linea.strip())

    return registros, descartadas


def guardar_resultados(base, out_dir, img_procesada_path, texto_ocr, registros, descartadas):
    """Guarda todos los resultados."""
    os.makedirs(out_dir, exist_ok=True)

    # Imagen procesada
    proc_dst = os.path.join(out_dir, f"{base}_procesada.png")
    subprocess.run(['cp', img_procesada_path, proc_dst])

    # Texto OCR raw
    txt_path = os.path.join(out_dir, f"{base}_ocr.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(texto_ocr)

    # CSV estructurado
    csv_path = os.path.join(out_dir, f"{base}_datos.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['TIPO', 'DOCUMENTO', 'NOMBRE', 'ESCUELA', 'CONFIANZA', 'RAW'])
        for r in registros:
            writer.writerow([r['tipo'], r['documento'], r['nombre'],
                           r['escuela'], r['confianza'], r['raw']])

    # JSON con todo (para la webapp)
    json_path = os.path.join(out_dir, f"{base}_resultado.json")
    data = {
        'pagina': base,
        'total_registros': len(registros),
        'filas_esperadas': FILAS_ESPERADAS,
        'completitud': round(len(registros) / FILAS_ESPERADAS * 100),
        'registros': registros,
        'descartadas': descartadas,
        'stats': {
            'con_dni': sum(1 for r in registros if r['documento']),
            'con_nombre': sum(1 for r in registros if r['nombre']),
            'con_escuela': sum(1 for r in registros if r['escuela']),
            'alta_confianza': sum(1 for r in registros if r['confianza'] >= 70),
            'media_confianza': sum(1 for r in registros if 30 <= r['confianza'] < 70),
        }
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return csv_path, json_path


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 procesar_padron.py <imagen.jpg> [--thresh N]")
        sys.exit(1)

    img_path = sys.argv[1]
    threshold = DEFAULT_THRESHOLD

    if '--thresh' in sys.argv:
        idx = sys.argv.index('--thresh')
        threshold = int(sys.argv[idx + 1])

    if not os.path.exists(img_path):
        print(f"Error: no se encuentra '{img_path}'")
        sys.exit(1)

    base = os.path.splitext(os.path.basename(img_path))[0]
    out_dir = os.path.join(os.path.dirname(img_path), '..', 'procesado')

    print(f"\n{'='*60}")
    print(f"PROCESANDO: {img_path} (threshold={threshold}%)")
    print(f"{'='*60}")

    # Preprocesar
    img_final_path, img_straight = preprocesar_imagen(img_path, threshold)

    # OCR
    print(f"  5. OCR (Tesseract PSM 4 + spa)...")
    texto = hacer_ocr(img_final_path)
    os.remove(img_final_path)

    # Post-proceso estructurado
    print(f"  6. Post-procesando estructura...")
    registros, descartadas = postprocesar(texto)

    # Guardar
    tmp_proc = '/tmp/padron_tmp_final.png'
    proc_path = os.path.join(out_dir, f"{base}_procesada.png")
    # Guardar la imagen enderezada como procesada
    cv2.imwrite(proc_path, img_straight)

    csv_path, json_path = guardar_resultados(base, out_dir, proc_path, texto, registros, descartadas)

    # Reporte
    stats_alta = sum(1 for r in registros if r['confianza'] >= 70)
    stats_media = sum(1 for r in registros if 30 <= r['confianza'] < 70)
    completitud = round(len(registros) / FILAS_ESPERADAS * 100)

    print(f"\n{'='*60}")
    print(f"RESULTADO: {base}")
    print(f"{'='*60}")
    print(f"  Registros parseados: {len(registros)}/{FILAS_ESPERADAS} ({completitud}%)")
    print(f"  Alta confianza (>=70): {stats_alta}")
    print(f"  Media confianza:       {stats_media}")
    print(f"  Lineas descartadas:    {len(descartadas)}")
    print(f"  CSV: {csv_path}")
    print(f"  JSON: {json_path}")

    print(f"\n--- Primeros 15 registros ---\n")
    for r in registros[:15]:
        conf = r['confianza']
        marca = '++' if conf >= 70 else '+ ' if conf >= 50 else '? '
        print(f"  {marca} {r['tipo']:3} | {r['documento']:>8} | {r['nombre']:<35} | {r['escuela']}")

    if len(registros) > 15:
        print(f"\n  ... y {len(registros) - 15} registros mas")

    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
