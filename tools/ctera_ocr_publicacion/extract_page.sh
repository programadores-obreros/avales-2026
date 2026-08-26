#!/usr/bin/env bash
# Extrae el texto de una pagina renderizada (page-NN.png) del boletin CTERA.
# Uso: extract_page.sh <page-NN.png> <output.txt> [slice_width_px]
set -euo pipefail

IMG="$1"
OUT="$2"
SLICE_W="${3:-375}"

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# 1. calcular bbox de contenido (ink) con python/numpy
read -r X0 Y0 X1 Y1 <<< "$(python3 - "$IMG" <<'EOF'
import sys
import numpy as np
from PIL import Image
im = Image.open(sys.argv[1]).convert("L")
arr = np.array(im)
h, w = arr.shape
dark = arr < 180
cols_any = dark.any(axis=0)
rows_any = dark.any(axis=1)
xs = np.where(cols_any)[0]
ys = np.where(rows_any)[0]
x0, x1 = int(xs.min()), int(xs.max())
y0, y1 = int(ys.min()), int(ys.max())
pad = int(0.01 * w)
x0 = max(x0 + pad, 0)
x1 = min(x1 - pad, w - 1)
y0 = max(y0 + pad, 0)
y1 = min(y1 - pad, h - 1)
print(x0, y0, x1, y1)
EOF
)"

WIDTH=$((X1 - X0))
HEIGHT=$((Y1 - Y0))
N_SLICES=$(( (WIDTH + SLICE_W - 1) / SLICE_W ))

echo "bbox=($X0,$Y0,$X1,$Y1) width=$WIDTH height=$HEIGHT slices=$N_SLICES" >&2

: > "$OUT"

# Recorrer de X1 hacia X0 (orden de lectura real)
for (( i=0; i<N_SLICES; i++ )); do
    SX1=$(( X1 - i*SLICE_W ))
    SX0=$(( SX1 - SLICE_W ))
    if (( SX0 < X0 )); then SX0=$X0; fi
    W=$(( SX1 - SX0 ))
    if (( W <= 0 )); then continue; fi

    RAW="$WORKDIR/slice_$i.png"
    BIN="$WORKDIR/slice_${i}_bin.png"
    ROT="$WORKDIR/slice_${i}_rot.png"

    magick "$IMG" -crop "${W}x${HEIGHT}+${SX0}+${Y0}" +repage "$RAW" 2>/dev/null
    magick "$RAW" -rotate -90 -colorspace gray -threshold 60% -resize 300% "$ROT" 2>/dev/null

    TXT=$(tesseract "$ROT" - -l spa --psm 6 2>/dev/null || true)
    echo "$TXT" >> "$OUT"
    echo "" >> "$OUT"
done

echo "OK: $OUT ($(wc -l < "$OUT") lineas)" >&2
