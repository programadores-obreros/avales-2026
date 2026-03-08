#!/usr/bin/env python3
"""
Genera datos JSON para la webapp de revisión de OCR.
Lee procesado/ + fotos originales → genera webapp/public/data/
"""

import json
import os
import re
import csv
import shutil
from PIL import Image, ImageOps

PROCESADO_DIR = 'procesado'
WEBAPP_DATA_DIR = 'webapp/public/data'


def buscar_fotos_originales():
    """Busca fotos_preparadas.json en subcarpetas de fotos/ y mapea pagina → ruta."""
    fotos_map = {}
    for root, dirs, files in os.walk('fotos'):
        if 'fotos_preparadas.json' in files:
            with open(os.path.join(root, 'fotos_preparadas.json')) as f:
                prep = json.load(f)
            for filename, info in prep.items():
                ruta = os.path.join(root, filename)
                if os.path.exists(ruta):
                    fotos_map[info['pagina']] = ruta
    return fotos_map


def main():
    os.makedirs(f'{WEBAPP_DATA_DIR}/fotos', exist_ok=True)
    os.makedirs(f'{WEBAPP_DATA_DIR}/procesadas', exist_ok=True)

    fotos_map = buscar_fotos_originales()

    paginas = []
    for f in sorted(os.listdir(PROCESADO_DIR)):
        m = re.match(r'pag_(\d+)_datos\.csv', f)
        if not m:
            continue
        pag_num = int(m.group(1))
        base = f'pag_{pag_num:04d}'

        # Leer CSV
        registros = []
        with open(os.path.join(PROCESADO_DIR, f), encoding='utf-8') as csvf:
            for row in csv.DictReader(csvf):
                registros.append(dict(row))

        # Leer OCR
        ocr_path = os.path.join(PROCESADO_DIR, f'{base}_ocr.txt')
        ocr_text = ''
        if os.path.exists(ocr_path):
            with open(ocr_path, encoding='utf-8') as tf:
                ocr_text = tf.read()

        # Copiar procesada
        proc_src = os.path.join(PROCESADO_DIR, f'{base}_procesada.png')
        if os.path.exists(proc_src):
            img = Image.open(proc_src)
            img.thumbnail((1200, 1600), Image.LANCZOS)
            img.save(f'{WEBAPP_DATA_DIR}/procesadas/{base}.png', 'PNG')

        # Copiar foto original (con EXIF transpose + resize)
        has_foto = False
        if pag_num in fotos_map:
            img = Image.open(fotos_map[pag_num])
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1200, 1600), Image.LANCZOS)
            img.save(f'{WEBAPP_DATA_DIR}/fotos/{base}.jpg', 'JPEG', quality=85)
            has_foto = True

        # Calidad
        calidad = min(100, round(len(registros) / 60 * 100))
        escuelas_ok = sum(1 for r in registros if r.get('ESCUELA', '') or r.get('DESTINO', ''))

        paginas.append({
            'id': base,
            'numero': pag_num,
            'calidad': calidad,
            'foto': f'data/fotos/{base}.jpg' if has_foto else '',
            'procesada': f'data/procesadas/{base}.png',
            'ocr': ocr_text,
            'registros': registros,
            'detalles': {
                'registros_extraidos': len(registros),
                'escuelas_detectadas': escuelas_ok,
                'esperados': 60,
            }
        })

        marca = "OK" if calidad >= 50 else "!!"
        print(f"  [{marca}] Pag {pag_num:>3}: {len(registros)} registros, {escuelas_ok} con escuela, calidad {calidad}%")

    paginas.sort(key=lambda p: p['numero'])

    with open(f'{WEBAPP_DATA_DIR}/paginas.json', 'w', encoding='utf-8') as f:
        json.dump(paginas, f, ensure_ascii=False, indent=2)

    print(f"\nGenerado: {len(paginas)} paginas en {WEBAPP_DATA_DIR}/")


if __name__ == '__main__':
    main()
