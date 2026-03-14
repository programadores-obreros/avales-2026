# Backup Produccion — 2026-03-14

Snapshot de TODOS los datos JSON servidos por Firebase Hosting en `https://suteba-2026.web.app/` al momento de la descarga.

## Archivos descargados

| Archivo | Bytes | Registros | Descripcion |
|---|---|---|---|
| `padron_avales.json` | 667,552 | 9,396 | Padron hibrido 2022+2026 para busqueda de candidatos |
| `tasks.json` | 2,509,883 | 4 keys | Tareas de verificacion CAPTCHA (voluntarios) |

## Archivos verificados como NO existentes en produccion (404)

- `data/control.json` — no deployado
- `data/paginas.json` — no deployado

## Checksums SHA256

```
faff3157b214c23f3e175d73c0b21b4b20025d50a82c61c873652a6957bb5a45  padron_avales.json
75ed67111b5619d5cbbf9252aa319629744ebfb9966f9ab970cd897fe417070a  tasks.json
```

## Origen de padron_avales.json

Generado por `tools/padron_avales_2026.py` — hibrido de:
- **Padron 2026 OCR v6**: `tools/table_ocr/results/padron_v6.json`
- **Gold 2022**: `tools/padron_2022/gold/padron_2022_gold.csv`

Logica: DNI en ambos → nombre gold 2022 + escuela 2026. Solo 2026 → datos OCR. Solo 2022 → datos gold.

## Estructura de cada registro en padron_avales.json

```json
{"d": "28191198", "n": "ABAISE ANGELA ELISABETH", "e": "0-069-MS-0140", "p": 1}
```

- `d`: DNI
- `n`: Nombre completo
- `e`: Escuela (formato `0-069-XX-NNNN`) o `JUBILADO/A`
- `p`: Pagina del padron provisorio

## Firebase project

- Project: `suteba-2026`
- URL: `https://suteba-2026.web.app/`
- Config: `webapp/.firebaserc` + `webapp/firebase.json`
