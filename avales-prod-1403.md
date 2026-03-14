# Avales Produccion — 14/03/2026

## URLs en produccion

- Planilla de candidatos: https://suteba-2026.web.app/planilla
- Padron JSON (API): https://suteba-2026.web.app/data/padron_avales.json

## Firebase

- Proyecto: `suteba-2026`
- Config: `13_mayo_2026/padron_provisorio/webapp/.firebaserc`

## Backup local del padron

- Ruta: `13_mayo_2026/padron_provisorio/webapp/backup_produccion_2026-03-14/padron_avales.json`
- Registros: 9,396
- Tamanio: 668 KB
- SHA256: `faff3157b214c23f3e175d73c0b21b4b20025d50a82c61c873652a6957bb5a45`

## Origen del padron

Generado por `tools/padron_avales_2026.py` — hibrido de:
- Padron 2026 OCR v6: `tools/table_ocr/results/padron_v6.json`
- Gold 2022: `tools/padron_2022/gold/padron_2022_gold.csv`

## Notas

- El JSON NO esta versionado en git (`.gitignore`: `**/public/data/*.json`)
- El backup descargado el 14/03/2026 es la unica copia local
- La planilla (`planilla.html`) consume este JSON via `fetch('data/padron_avales.json')`
