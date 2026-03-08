#!/usr/bin/env python3
"""
Prueba múltiples estrategias de preprocesamiento para encontrar la mejor.
Uso: python3 test_estrategias.py fotos/pag159.jpg
"""

import sys
import os
import cv2
import numpy as np
from PIL import Image, ExifTags
import pytesseract


def corregir_orientacion_exif(img_path):
    """Corrige la orientación según EXIF."""
    pil_img = Image.open(img_path)
    try:
        exif = pil_img._getexif()
        if exif:
            for tag, value in exif.items():
                if ExifTags.TAGS.get(tag) == 'Orientation':
                    if value == 6:
                        pil_img = pil_img.rotate(-90, expand=True)
                    elif value == 3:
                        pil_img = pil_img.rotate(180, expand=True)
                    elif value == 8:
                        pil_img = pil_img.rotate(90, expand=True)
                    break
    except (AttributeError, KeyError):
        pass
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def ocr(img, nombre):
    """Ejecuta OCR y retorna texto."""
    config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
    texto = pytesseract.image_to_string(img, lang='spa', config=config)
    lineas = [l for l in texto.strip().split('\n') if l.strip()]
    return texto, lineas


def estrategia_1_solo_gris(img_bgr):
    """Solo escala de grises, sin más procesamiento."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return gray


def estrategia_2_gris_otsu(img_bgr):
    """Escala de grises + binarización OTSU."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def estrategia_3_denoise_adaptive(img_bgr):
    """Gris + denoise + adaptive threshold (blockSize más grande)."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 51, 20)
    return binary


def estrategia_4_clahe_otsu(img_bgr):
    """CLAHE (ecualización adaptativa de histograma) + OTSU."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def estrategia_5_clahe_denoise_adaptive(img_bgr):
    """CLAHE + denoise + adaptive threshold."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(enhanced, h=12)
    binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 51, 15)
    return binary


def estrategia_6_sharpen_antes_binarizar(img_bgr):
    """Gris + sharpen + denoise + OTSU (sharpen ANTES de binarizar)."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    denoised = cv2.fastNlMeansDenoising(sharpened, h=10)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def estrategia_7_resize_up(img_bgr):
    """Escalar x1.5 + gris + CLAHE + OTSU (más resolución para Tesseract)."""
    h, w = img_bgr.shape[:2]
    resized = cv2.resize(img_bgr, (int(w * 1.5), int(h * 1.5)), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def estrategia_8_morph_cleanup(img_bgr):
    """CLAHE + OTSU + operaciones morfológicas para limpiar ruido."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Limpiar ruido con operación morfológica
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned


ESTRATEGIAS = [
    ("1_solo_gris", estrategia_1_solo_gris),
    ("2_gris_otsu", estrategia_2_gris_otsu),
    ("3_denoise_adaptive", estrategia_3_denoise_adaptive),
    ("4_clahe_otsu", estrategia_4_clahe_otsu),
    ("5_clahe_denoise_adaptive", estrategia_5_clahe_denoise_adaptive),
    ("6_sharpen_antes_binarizar", estrategia_6_sharpen_antes_binarizar),
    ("7_resize_up", estrategia_7_resize_up),
    ("8_morph_cleanup", estrategia_8_morph_cleanup),
]


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_estrategias.py <imagen.jpg>")
        sys.exit(1)

    img_path = sys.argv[1]
    base = os.path.splitext(os.path.basename(img_path))[0]
    out_dir = os.path.join(os.path.dirname(img_path), '..', 'test_estrategias')
    os.makedirs(out_dir, exist_ok=True)

    print(f"Cargando y corrigiendo orientación: {img_path}")
    img = corregir_orientacion_exif(img_path)
    print(f"Dimensiones: {img.shape[1]}x{img.shape[0]}\n")

    resultados = []

    for nombre, fn in ESTRATEGIAS:
        print(f"Probando estrategia: {nombre}...", end=" ", flush=True)
        procesada = fn(img)

        # Guardar imagen procesada
        img_out = os.path.join(out_dir, f"{base}_{nombre}.png")
        cv2.imwrite(img_out, procesada)

        # OCR
        texto, lineas = ocr(procesada, nombre)

        # Guardar texto
        txt_out = os.path.join(out_dir, f"{base}_{nombre}.txt")
        with open(txt_out, 'w', encoding='utf-8') as f:
            f.write(texto)

        # Heurística de calidad: contar líneas con palabras "reales" (>3 chars)
        lineas_utiles = [l for l in lineas if any(len(w) > 3 for w in l.split())]
        score = len(lineas_utiles)

        resultados.append((nombre, score, len(lineas), lineas_utiles[:3]))
        print(f"{score} lineas utiles / {len(lineas)} total")

    # Ranking
    resultados.sort(key=lambda x: x[1], reverse=True)
    print(f"\n{'='*60}")
    print("RANKING DE ESTRATEGIAS")
    print(f"{'='*60}")
    for i, (nombre, score, total, preview) in enumerate(resultados, 1):
        print(f"\n  #{i} {nombre}: {score} lineas utiles ({total} total)")
        for linea in preview:
            print(f"      | {linea[:80]}")

    mejor = resultados[0][0]
    print(f"\n  MEJOR: {mejor}")
    print(f"  Revisa en: {out_dir}/")
    print(f"  Archivos: {base}_{mejor}.txt y {base}_{mejor}.png")


if __name__ == '__main__':
    main()
