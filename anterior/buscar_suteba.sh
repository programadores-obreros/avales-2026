#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/sda1"
OUT_DIR="$PWD/busquedas_suteba"
TS="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT_DIR"

OUT_ALL="$OUT_DIR/suteba_all_$TS.txt"
OUT_DIRS="$OUT_DIR/suteba_dirs_$TS.txt"
OUT_FILES="$OUT_DIR/suteba_files_$TS.txt"

# Nota: -iname = case-insensitive; -print0 + sort -z por seguridad con espacios
find "$ROOT" -xdev \( -iname '*suteba*' \) -print0 2>/dev/null \
  | sort -z \
  | tr '\0' '\n' \
  | tee "$OUT_ALL" >/dev/null

# Separar dirs y files
grep -E '/$' "$OUT_ALL" >/dev/null 2>&1 || true

# Clasificar consultando el filesystem (robusto)
: > "$OUT_DIRS"
: > "$OUT_FILES"
while IFS= read -r p; do
  [ -z "$p" ] && continue
  if [ -d "$p" ]; then
    echo "$p" >> "$OUT_DIRS"
  elif [ -f "$p" ]; then
    echo "$p" >> "$OUT_FILES"
  else
    echo "$p" >> "$OUT_ALL"
  fi
done < "$OUT_ALL"

echo "Listo."
echo "Resultados:"
echo " - Todo:        $OUT_ALL"
echo " - Carpetas:    $OUT_DIRS"
echo " - Archivos:    $OUT_FILES"
