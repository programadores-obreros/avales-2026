#!/usr/bin/env python3
"""
Procesa fotos preparadas con la herramienta web.
Lee fotos_preparadas.json → rota → cropea → Claude Vision OCR → tabla CSV.

Uso: python3 procesar_preparadas.py fotos/Primera_tanda/drive/primera/
"""

import sys
import os
import re
import csv
import json
import time
import base64
import cv2
import numpy as np
from PIL import Image, ImageOps

import anthropic


CLAUDE_MODEL = "claude-sonnet-4-6"

VISION_PROMPT = """\
Extraé datos de una página fotografiada de un padrón sindical de SUTEBA 2026.
La imagen contiene UNA tabla principal con filas de personas.

{page_instruction}

ESTRUCTURA DE CADA FILA (4 columnas):
1. TIPO: "DNI", "LC" o "LE" (generalmente "DNI")
2. DOCUMENTO: número de 7 u 8 dígitos, sin puntos
3. APELLIDO Y NOMBRE: texto en MAYUSCULAS
4. ESCUELA/DESTINO: código con formato 0-069-XX-XXXX (donde XX son siglas de 2 letras como MS, PP, MT, DM, EE, FP, SC, AA, IS, etc. y XXXX son 4 dígitos), o "JUBILADO/A", o "AP. EN SEDE"

REGLAS DE INTERPRETACION:
- tipo: si no se lee bien, usá "DNI" como default
- documento: SOLO dígitos, 7 u 8. Si no se lee bien, dejá ""
- nombre: transcribí EXACTO como aparece, en MAYUSCULAS. NO corrijas ortografía. NO completes por contexto
- destino: código 0-069-XX-XXXX, o "JUBILADO/A", o "AP. EN SEDE", o "" si no se lee

INSTRUCCIONES IMPORTANTES:
- Extraé TODAS las filas visibles, no te saltees ninguna
- Si un campo no se lee, dejalo vacío "". NO inventes datos
- NO completes información por contexto o inferencia
- Incluí filas aunque tengan campos ilegibles (mejor una fila incompleta que perderla)
- Ignorá encabezados de columna y textos que no sean filas de datos
- Si tenés dudas sobre un valor, agregá el campo "observacion" con la duda

CONTROL DE CALIDAD INTERNO:
Antes de responder, revisá que no te hayas salteado filas contando las que ves en la imagen.

SALIDA: Respondé SOLO con un JSON object, sin markdown, sin backticks:
{{"pagina": 148, "registros": [{{"tipo": "DNI", "documento": "12345678", "nombre": "APELLIDO NOMBRE", "destino": "0-069-MS-0001"}}]}}

El campo "observacion" es opcional, solo agregalo si tenés dudas sobre algún valor en esa fila."""

PAGE_INSTRUCTION_AUTO = "Necesito que leas el número de página visible en la hoja (suele estar abajo a la derecha)."
PAGE_INSTRUCTION_KNOWN = "El número de página es {pagina}."


def _preprocess_for_vision(gray):
    """Preproceso ligero para visión: CLAHE si baja calidad + resize."""
    img_std = gray.std()
    if img_std < 17:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    h, w = gray.shape
    max_w = 1500
    if w > max_w:
        scale = max_w / w
        gray = cv2.resize(gray, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA)

    return gray


def _image_to_base64(gray):
    """Convierte imagen grayscale OpenCV a base64 JPEG."""
    success, buffer = cv2.imencode('.jpg', gray, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        raise RuntimeError("Error codificando imagen a JPEG")
    return base64.standard_b64encode(buffer).decode('utf-8')


def _call_claude_vision(client, img_base64, pagina_conocida=None):
    """Llama a Claude Vision y devuelve (pagina_detectada, registros, raw_text)."""
    if pagina_conocida and pagina_conocida > 0:
        page_inst = PAGE_INSTRUCTION_KNOWN.format(pagina=pagina_conocida)
    else:
        page_inst = PAGE_INSTRUCTION_AUTO

    prompt = VISION_PROMPT.format(page_instruction=page_inst)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_base64,
                    }
                },
                {"type": "text", "text": prompt},
            ]
        }]
    )

    raw_text = response.content[0].text.strip()

    # Limpiar posibles backticks markdown
    if raw_text.startswith("```"):
        raw_text = re.sub(r'^```\w*\n?', '', raw_text)
        raw_text = re.sub(r'\n?```$', '', raw_text)
        raw_text = raw_text.strip()

    data = json.loads(raw_text)

    # Extraer página detectada
    pagina_detectada = data.get('pagina')
    if pagina_detectada is not None:
        try:
            pagina_detectada = int(pagina_detectada)
        except (ValueError, TypeError):
            pagina_detectada = None

    registros_raw = data.get('registros', [])

    registros = []
    for r in registros_raw:
        tipo = str(r.get('tipo', 'DNI')).strip().upper()
        documento = re.sub(r'[^\d]', '', str(r.get('documento', '')))
        nombre = str(r.get('nombre', '')).strip().upper()
        destino = str(r.get('destino', '')).strip().upper()
        observacion = str(r.get('observacion', '')).strip() if r.get('observacion') else ''

        # Normalizar tipo
        if tipo not in ('DNI', 'LC', 'LE'):
            tipo = 'DNI'

        # Validar documento: 7-8 dígitos o vacío (no descartar fila)
        if documento and not (7 <= len(documento) <= 8):
            observacion = f"DOC original: {documento}. {observacion}".strip()
            documento = ''

        # Fila sin nombre Y sin documento = basura, saltear
        if len(nombre) < 2 and not documento:
            continue

        # Normalizar destino
        if destino and destino not in ('JUBILADO/A', 'AP. EN SEDE', ''):
            m = re.match(r'0-069-[A-Z]{2}-\d{4}$', destino)
            if not m:
                observacion = f"Destino original: {destino}. {observacion}".strip()
                destino = ''

        reg = {
            'tipo': tipo,
            'documento': documento,
            'nombre': nombre,
            'destino': destino,
        }
        if observacion:
            reg['observacion'] = observacion
        registros.append(reg)

    return pagina_detectada, registros, raw_text


def procesar_una_pagina(img_path, rotacion, crop, pagina_num, out_dir, client):
    """Procesa una sola página: rota, cropea, Claude Vision OCR, parsea."""
    base = f"pag_{pagina_num:04d}"
    print(f"\n{'='*60}")
    print(f"PAGINA {pagina_num} ({os.path.basename(img_path)})")
    print(f"{'='*60}")

    # 1. Cargar y corregir EXIF
    print("  1. Cargando imagen...")
    img = Image.open(img_path)
    img = ImageOps.exif_transpose(img)
    print(f"     Transposed: {img.size[0]}x{img.size[1]}")

    # 2. Rotar
    if rotacion and rotacion > 0:
        img = img.rotate(-rotacion, expand=True)
        print(f"  2. Rotada {rotacion} -> {img.size[0]}x{img.size[1]}")
    else:
        print(f"  2. Sin rotacion necesaria")

    # 3. Crop
    if crop:
        x, y, w, h = crop['x'], crop['y'], crop['w'], crop['h']
        img = img.crop((x, y, x + w, y + h))
        print(f"  3. Cropeada -> {img.size[0]}x{img.size[1]}")
    else:
        print(f"  3. Sin crop")

    # 4. Convertir a grayscale
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    # 5. Evaluar calidad
    img_std = gray.std()
    img_range = int(gray.max()) - int(gray.min())
    print(f"  4. Calidad: std={img_std:.1f} rango={img_range}")

    if img_std < 16 or img_range < 170:
        print(f"     BAJA CALIDAD - pero Claude Vision deberia manejarla")

    # 6. Preproceso para vision
    processed = _preprocess_for_vision(gray)
    img_b64 = _image_to_base64(processed)
    print(f"  5. Imagen preparada: {processed.shape[1]}x{processed.shape[0]}, base64={len(img_b64)//1024}KB")

    # 7. Claude Vision OCR
    auto_pagina = pagina_num == 0
    print(f"  6. Llamando Claude Vision ({CLAUDE_MODEL}){'  [auto-detectar pagina]' if auto_pagina else ''}...")
    try:
        pagina_detectada, registros, raw_text = _call_claude_vision(
            client, img_b64, pagina_conocida=pagina_num if not auto_pagina else None
        )
        if auto_pagina and pagina_detectada:
            pagina_num = pagina_detectada
            base = f"pag_{pagina_num:04d}"
            print(f"     -> Pagina detectada: {pagina_num}")
        elif auto_pagina:
            print(f"     -> No se pudo detectar pagina, usando nombre de archivo")
            pagina_num = hash(os.path.basename(img_path)) % 9000 + 1000
            base = f"pag_{pagina_num:04d}"
        print(f"     -> {len(registros)} registros extraidos")
    except (anthropic.APIError, json.JSONDecodeError, KeyError) as e:
        print(f"     ERROR: {type(e).__name__}: {e}")
        pagina_detectada, registros, raw_text = None, [], f"ERROR: {e}"

    # Guardar imagen procesada
    proc_path = os.path.join(out_dir, f"{base}_procesada.png")
    cv2.imwrite(proc_path, processed)

    # Guardar respuesta raw (JSON de Claude)
    txt_path = os.path.join(out_dir, f"{base}_ocr.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(raw_text)

    # Guardar CSV
    csv_path = os.path.join(out_dir, f"{base}_datos.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['TIPO', 'DNI', 'APELLIDO_NOMBRE', 'ESCUELA', 'OBSERVACION'])
        for r in registros:
            writer.writerow([r['tipo'], r['documento'], r['nombre'], r['destino'], r.get('observacion', '')])

    print(f"\n  Resultados guardados:")
    print(f"    OCR raw:  {txt_path}")
    print(f"    CSV:      {csv_path}")
    print(f"    Imagen:   {proc_path}")

    calidad = "BUENA" if len(registros) >= 30 else "REGULAR" if len(registros) >= 15 else "MALA"
    print(f"    Calidad:  {calidad} ({len(registros)}/~60 filas)")

    return pagina_num, registros, raw_text, calidad


def _generar_resultado_json(resultados_por_archivo):
    """Genera JSON en el mismo formato que resultado_IA.json para comparar."""
    files = []
    for res in resultados_por_archivo:
        rows = []
        for r in res['registros']:
            row = {"tipo": r['tipo'], "dni": r['documento'], "name": r['nombre']}
            destino = r['destino']
            if destino == 'JUBILADO/A':
                row["status"] = "JUBILADO"
            elif destino == 'AP. EN SEDE':
                row["status"] = "AP. EN SEDE"
            elif destino and re.match(r'0-069-([A-Z]{2})-(\d{4})$', destino):
                m = re.match(r'0-069-([A-Z]{2})-(\d{4})$', destino)
                row["school_type"] = m.group(1)
                row["school_number"] = m.group(2)
            if r.get('observacion'):
                row["observacion"] = r['observacion']
            rows.append(row)
        files.append({"file": res['archivo'], "rows": rows})
    return {"files": files}


def imprimir_tabla(registros, pagina_num):
    """Imprime la tabla formateada."""
    print(f"\n{'='*90}")
    print(f"  TABLA PAGINA {pagina_num}: {len(registros)} registros")
    print(f"{'='*90}")
    print(f"  {'#':>3} {'TIPO':>4} {'DOCUMENTO':>10}  {'APELLIDO Y NOMBRE':<38} {'DESTINO':<16} {'OBS'}")
    print(f"  {'-'*88}")
    for i, r in enumerate(registros, 1):
        obs = r.get('observacion', '')
        obs_short = obs[:20] + '...' if len(obs) > 20 else obs
        print(f"  {i:>3} {r['tipo']:>4} {r['documento']:>10}  {r['nombre']:<38} {r['destino']:<16} {obs_short}")
    print(f"  {'-'*88}")
    print(f"  Total: {len(registros)} registros\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 procesar_preparadas.py <carpeta_con_json>")
        sys.exit(1)

    carpeta = sys.argv[1].rstrip('/')
    json_path = os.path.join(carpeta, 'fotos_preparadas.json')

    if not os.path.exists(json_path):
        print(f"Error: no se encuentra '{json_path}'")
        sys.exit(1)

    # Verificar API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY no esta configurada.")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    client = anthropic.Anthropic()
    print(f"  Claude Vision: {CLAUDE_MODEL}")

    with open(json_path, 'r') as f:
        preparadas = json.load(f)

    out_dir = 'procesado'
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'#'*60}")
    print(f"  PROCESANDO {len(preparadas)} PAGINAS PREPARADAS")
    print(f"{'#'*60}")

    total_registros = 0
    resumen = []
    resultados_por_archivo = []
    paginas = sorted(preparadas.items(), key=lambda x: x[1]['pagina'])

    for i, (filename, info) in enumerate(paginas):
        img_path = os.path.join(carpeta, filename)
        if not os.path.exists(img_path):
            print(f"\n  ERROR: no se encuentra {img_path}")
            continue

        pagina_final, registros, texto, calidad = procesar_una_pagina(
            img_path,
            info['rotacion'],
            info.get('crop'),
            info['pagina'],
            out_dir,
            client,
        )

        imprimir_tabla(registros, pagina_final)
        total_registros += len(registros)
        resumen.append({
            'pagina': pagina_final,
            'registros': len(registros),
            'calidad': calidad,
            'archivo': filename,
        })
        resultados_por_archivo.append({
            'archivo': filename,
            'registros': registros,
        })

        # Rate limiting: esperar entre llamadas a la API
        if i < len(paginas) - 1:
            time.sleep(1)

    # Generar JSON de comparacion (mismo formato que resultado_IA.json)
    resultado_json = _generar_resultado_json(resultados_por_archivo)
    resultado_path = os.path.join(out_dir, 'resultado_claude.json')
    with open(resultado_path, 'w', encoding='utf-8') as f:
        json.dump(resultado_json, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON comparacion: {resultado_path}")

    print(f"\n{'#'*60}")
    print(f"  RESUMEN: {total_registros} registros en {len(preparadas)} paginas")
    print(f"{'#'*60}")

    for r in resumen:
        marca = "OK" if r['calidad'] == 'BUENA' else "!!" if r['calidad'] == 'MALA' else "? "
        print(f"  [{marca}] Pag {r['pagina']:>3}: {r['registros']:>3} registros ({r['calidad']})")

    malas = [r for r in resumen if r['calidad'] == 'MALA']
    if malas:
        print(f"\n  ATENCION: {len(malas)} paginas necesitan RE-FOTOGRAFIARSE:")
        for r in malas:
            print(f"    - Pagina {r['pagina']} ({r['archivo']})")

    print()


if __name__ == '__main__':
    main()
