#!/usr/bin/env python3
"""Detecta candidatos a encabezado de localidad/seccion en el texto OCR
de una pagina del boletin CTERA.

v2: ancla el patron directamente a "MESA<digitos>" en vez de buscar dos
puntos sueltos -- distintas paginas usan distinta puntuacion antes de
"MESA" (Mendoza usa ":", SUTEBA/Bs.As. usa ","), un scan libre de dos
puntos se perdia todos los encabezados de SUTEBA. Anclar a MESA generaliza
a ambos estilos sin depender de que puntuacion usa cada sindicato.

Precision/recall medidos a mano:
- Mendoza (pagina 4, colon-style): ~76% precision, ~83% recall (15/18
  departamentos reales detectados).
- SUTEBA Bs.As. (pagina 10, comma-style): ~91% precision (20/22 candidatos
  eran distritos reales: Monte Grande, Adrogue, Chacabuco, Chascomus, etc.)
Son CANDIDATOS a revisar, no verdad verificada -- no usar como fuente
unica sin revision humana.

Uso: detect_headers.py out_pageNN_full.txt
"""
import sys, re, json

HEADER_RE = re.compile(
    r'\b([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9°ªÜ\. ]{1,35}?)[.,:;]\s*MESA[^\d]{0,4}\d'
)

RUIDO = re.compile(
    r'\b(ESC|ESCUELA|CALLE|RUTA|AV|N°|Nº|N"|N9|MESA|SEDE|JARDIN|COL|CTRO|CENTRO|KM|'
    r'BARRIO|B°|PROV|S/N|RAFFO|MEDRANO|BORBOLLÓN|MONTENEGRO|'
    r'PP|MS|DC|DE|DM|JI|SC|MT|MA|FC|TH)\b',
    re.IGNORECASE
)

FECHAS_CONOCIDAS = re.compile(r'^(3 DE FEBRERO|25 DE MAYO|9 DE JULIO)$', re.IGNORECASE)

def detect(text):
    candidatos = []
    for m in HEADER_RE.finditer(text):
        label = m.group(1).strip()
        words = label.split()
        if len(words) > 4:
            continue
        if RUIDO.search(label):
            continue
        if any(ch.isdigit() for ch in label) and not FECHAS_CONOCIDAS.match(label):
            continue
        candidatos.append({"pos": m.start(), "label": label})
    return candidatos

def main(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    text = " ".join(l.strip() for l in raw.splitlines() if l.strip())
    text = re.sub(r"\s+", " ", text)
    candidatos = detect(text)
    print(json.dumps({"archivo": path, "candidatos": candidatos, "total": len(candidatos)},
                      ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main(sys.argv[1])
