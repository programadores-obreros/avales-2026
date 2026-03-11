#!/usr/bin/env python3
"""Generate verification tasks with cross-validation between OCR and prod sources.

Reads OCR JSON files from la_matanza/ocr_output/ (Source A) and cross-references
each record against padron_2026_final.json (Source B) by DNI. Classifies each
record's priority based on match quality and outputs a single tasks.json for the
volunteer CAPTCHA verification app.

Priority classification:
  - ALTA:  DNI not found in prod, or DNI is empty (likely OCR error)
  - MEDIA: DNI matches but nombre OR escuela differ
  - BAJA:  everything matches

Usage:
    python -m tools.generate_verification_tasks [--resize]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent / "13_mayo_2026" / "padron_provisorio"
OCR_DIR = BASE_DIR / "la_matanza" / "ocr_output"
IMAGE_DIR = BASE_DIR / "la_matanza" / "nueva_tanda"
PROD_FILE = BASE_DIR / "preproduccion" / "padron_2026_final.json"
WEBAPP_DATA = BASE_DIR / "webapp" / "public" / "data" / "verificacion"
OUTPUT_IMAGES = WEBAPP_DATA / "images"

SKIP_FILES = {"batch_state.json", "quality_report.txt"}

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ProdRecord(TypedDict, total=False):
    dni: str
    tipo: str
    nombre: str
    escuela_2026: str
    escuela_2022: str
    pagina: int
    validacion: str
    observacion: str


class RecordOut(TypedDict, total=False):
    row: int
    tipo: str
    documento: str
    nombre: str
    destino: str
    priority: str
    prod: dict[str, str] | None
    diff: list[str]


class TaskStats(TypedDict):
    alta: int
    media: int
    baja: int


class TaskOut(TypedDict, total=False):
    id: str
    image: str
    ocr_page: int
    total_records: int
    calidad: str
    priority: str
    stats: TaskStats
    records: list[RecordOut]


# ---------------------------------------------------------------------------
# Text normalization & comparison
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    """Strip accents, collapse whitespace, uppercase."""
    if not text:
        return ""
    # Decompose unicode, strip combining marks (accents)
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Uppercase, collapse whitespace
    return re.sub(r"\s+", " ", stripped.upper().strip())


def names_match(a: str, b: str) -> bool:
    """Compare names ignoring accents, extra spaces, and minor OCR errors."""
    na = normalize(a)
    nb = normalize(b)
    if not na or not nb:
        return na == nb
    if na == nb:
        return True
    # Allow fuzzy match for strings > 5 chars
    if len(na) > 5 and len(nb) > 5:
        matches = sum(1 for ca, cb in zip(na, nb) if ca == cb)
        return matches / max(len(na), len(nb)) > 0.85
    return False


def escuelas_match(ocr_destino: str, prod_escuela: str) -> bool:
    """Compare OCR destino against prod escuela_2026."""
    a = normalize(ocr_destino)
    b = normalize(prod_escuela)
    if not a or not b:
        return a == b
    if a == b:
        return True
    # Both empty-ish
    if not a and not b:
        return True
    return False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_prod_index() -> dict[str, ProdRecord]:
    """Load Source B and index by DNI."""
    if not PROD_FILE.exists():
        print(f"ERROR: Prod file not found at {PROD_FILE}")
        sys.exit(1)

    with open(PROD_FILE, encoding="utf-8") as f:
        data = json.load(f)

    registros: list[dict] = data.get("registros", [])
    index: dict[str, ProdRecord] = {}

    for reg in registros:
        dni = str(reg.get("dni", "")).strip()
        if dni:
            index[dni] = reg  # type: ignore[assignment]

    print(f"  Prod: {len(registros)} registros, {len(index)} DNIs únicos indexados")
    return index


def load_ocr_files(prod_index: dict[str, ProdRecord]) -> tuple[list[TaskOut], dict[str, int]]:
    """Load OCR JSONs and cross-validate against prod.

    Returns:
        tasks: list of task objects with cross-validation data
        global_stats: aggregate counts of ALTA/MEDIA/BAJA
    """
    tasks: list[TaskOut] = []
    global_stats: dict[str, int] = {"alta": 0, "media": 0, "baja": 0}

    for root, _dirs, files in os.walk(OCR_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json") or fname in SKIP_FILES:
                continue

            path = os.path.join(root, fname)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            registros = data.get("registros", [])
            if not registros:
                continue

            # Image filename matches JSON filename
            image_name = fname.replace(".json", ".jpg")
            image_path = IMAGE_DIR / image_name
            if not image_path.exists():
                print(f"  WARN: no image for {fname}, skipping")
                continue

            # Build task ID
            task_id = fname.replace(".json", "").replace(" ", "_")
            task_id = re.sub(r"[^a-zA-Z0-9_-]", "", task_id)

            task_stats: TaskStats = {"alta": 0, "media": 0, "baja": 0}
            records: list[RecordOut] = []

            for i, reg in enumerate(registros):
                documento = str(reg.get("documento", "")).strip()
                ocr_nombre = reg.get("nombre", "") or ""
                ocr_destino = reg.get("destino", "") or ""
                ocr_tipo = reg.get("tipo", "DNI") or "DNI"

                record: RecordOut = {
                    "row": i + 1,
                    "tipo": ocr_tipo,
                    "documento": documento,
                    "nombre": ocr_nombre,
                    "destino": ocr_destino,
                    "priority": "ALTA",
                    "prod": None,
                    "diff": [],
                }

                if not documento:
                    # Empty DNI → ALTA
                    record["priority"] = "ALTA"
                    task_stats["alta"] += 1
                    global_stats["alta"] += 1
                    records.append(record)
                    continue

                prod_rec = prod_index.get(documento)

                if prod_rec is None:
                    # DNI not found in prod → ALTA
                    record["priority"] = "ALTA"
                    task_stats["alta"] += 1
                    global_stats["alta"] += 1
                    records.append(record)
                    continue

                # DNI found — compare fields
                prod_nombre = prod_rec.get("nombre", "") or ""
                prod_escuela = prod_rec.get("escuela_2026", "") or ""

                record["prod"] = {
                    "dni": documento,
                    "nombre": prod_nombre,
                    "escuela": prod_escuela,
                }

                diffs: list[str] = []

                if not names_match(ocr_nombre, prod_nombre):
                    diffs.append("nombre")

                if not escuelas_match(ocr_destino, prod_escuela):
                    diffs.append("destino")

                record["diff"] = diffs

                if diffs:
                    record["priority"] = "MEDIA"
                    task_stats["media"] += 1
                    global_stats["media"] += 1
                else:
                    record["priority"] = "BAJA"
                    task_stats["baja"] += 1
                    global_stats["baja"] += 1

                records.append(record)

            # Task-level priority: highest among records
            if task_stats["alta"] > 0:
                task_priority = "ALTA"
            elif task_stats["media"] > 0:
                task_priority = "MEDIA"
            else:
                task_priority = "BAJA"

            task: TaskOut = {
                "id": task_id,
                "image": image_name,
                "ocr_page": data.get("pagina", 0),
                "total_records": len(records),
                "calidad": data.get("calidad", ""),
                "priority": task_priority,
                "stats": task_stats,
                "records": records,
            }

            tasks.append(task)

    # Sort by image name for consistent ordering
    tasks.sort(key=lambda t: t["image"])
    return tasks, global_stats


# ---------------------------------------------------------------------------
# Image resizing
# ---------------------------------------------------------------------------


def resize_images(tasks: list[TaskOut], target_width: int = 1200) -> None:
    """Resize images for web deployment."""
    try:
        import cv2  # type: ignore[import-untyped]
    except ImportError:
        print("ERROR: opencv-python required for resize. pip install opencv-python")
        sys.exit(1)

    OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)

    total = len(tasks)
    resized = 0
    for i, task in enumerate(tasks):
        src = IMAGE_DIR / task["image"]
        dst = OUTPUT_IMAGES / task["image"]

        if dst.exists():
            continue

        img = cv2.imread(str(src))
        if img is None:
            print(f"  WARN: can't read {src}")
            continue

        h, w = img.shape[:2]
        new_h = h
        if w > target_width:
            scale = target_width / w
            new_h = int(h * scale)
            img = cv2.resize(img, (target_width, new_h), interpolation=cv2.INTER_AREA)

        cv2.imwrite(str(dst), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        size_kb = dst.stat().st_size / 1024
        resized += 1
        print(f"  [{i + 1}/{total}] {task['image']} → {target_width}x{new_h} ({size_kb:.0f}KB)")

    print(f"\nResized {resized} images to {OUTPUT_IMAGES}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate verification tasks with cross-validation")
    parser.add_argument("--resize", action="store_true", help="Resize images for web")
    args = parser.parse_args()

    print("Loading prod data (Source B)...")
    prod_index = load_prod_index()

    print("Loading OCR files and cross-validating...")
    tasks, global_stats = load_ocr_files(prod_index)

    total_records = sum(t["total_records"] for t in tasks)
    total_classified = global_stats["alta"] + global_stats["media"] + global_stats["baja"]
    match_rate = global_stats["baja"] / total_classified if total_classified > 0 else 0.0

    print(f"  {len(tasks)} tasks, {total_records} total records")
    print(f"  ALTA: {global_stats['alta']}  MEDIA: {global_stats['media']}  BAJA: {global_stats['baja']}")
    print(f"  Match rate: {match_rate:.2%}")

    # Write tasks.json
    WEBAPP_DATA.mkdir(parents=True, exist_ok=True)
    output_path = WEBAPP_DATA / "tasks.json"
    output = {
        "total_tasks": len(tasks),
        "total_records": total_records,
        "stats": {
            "alta": global_stats["alta"],
            "media": global_stats["media"],
            "baja": global_stats["baja"],
            "match_rate": round(match_rate, 4),
        },
        "tasks": tasks,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Written to {output_path}")

    if args.resize:
        print("\nResizing images...")
        resize_images(tasks)

    # Summary
    alta_tasks = sum(1 for t in tasks if t["priority"] == "ALTA")
    media_tasks = sum(1 for t in tasks if t["priority"] == "MEDIA")
    baja_tasks = sum(1 for t in tasks if t["priority"] == "BAJA")

    print()
    print("=" * 60)
    print(f"  Tasks:          {len(tasks)}")
    print(f"  Records:        {total_records}")
    print(f"  Avg rec/task:   {total_records / len(tasks):.1f}" if tasks else "")
    print(f"  Match rate:     {match_rate:.2%}")
    print(f"  ---")
    print(f"  Records ALTA:   {global_stats['alta']}")
    print(f"  Records MEDIA:  {global_stats['media']}")
    print(f"  Records BAJA:   {global_stats['baja']}")
    print(f"  ---")
    print(f"  Tasks ALTA:     {alta_tasks}")
    print(f"  Tasks MEDIA:    {media_tasks}")
    print(f"  Tasks BAJA:     {baja_tasks}")
    print("=" * 60)


if __name__ == "__main__":
    main()
