"""Batch processor for SUTEBA padron OCR — Claude Vision.

Processes all images in nueva_tanda/ with Claude Vision, tracks state
for resume support, selects best variant per page group, and exports
combined results.

Usage:
    python -m tools.batch_processor sample   # 2 per group, validate quality
    python -m tools.batch_processor full     # all 172 images
    python -m tools.batch_processor report   # quality report from results
    python -m tools.batch_processor combine  # best-per-group → single CSV
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Project root so we can import ocr_engine
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ocr_engine.pipeline import SingleImagePipeline
from ocr_engine.output import OutputWriter
from ocr_engine.models import PageResult


# ---------- configuration ----------

BASE_DIR = PROJECT_ROOT / "13_mayo_2026" / "padron_provisorio" / "la_matanza"
IMAGE_DIR = BASE_DIR / "nueva_tanda"
CORRECTED_DIR = BASE_DIR / "nueva_tanda_corregidas"
OUTPUT_DIR = BASE_DIR / "ocr_output"
STATE_FILE = OUTPUT_DIR / "batch_state.json"
REPORT_FILE = OUTPUT_DIR / "quality_report.txt"
COMBINED_CSV = OUTPUT_DIR / "padron_la_matanza_combinado.csv"

FILAS_ESPERADAS = 60
ANOMALY_LOW = 40
ANOMALY_HIGH = 65
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


# ---------- image discovery ----------

def discover_images(image_dir: Path) -> dict[str, list[Path]]:
    """Group images by page prefix.

    Naming convention:
      pag_NNNN.jpg          → base image
      pag_NNNN (K).jpg      → variant K

    Returns dict: page_prefix → sorted list of image paths.
    """
    groups: dict[str, list[Path]] = {}
    for f in sorted(image_dir.iterdir()):
        if f.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        # Extract page prefix: "pag_0001" from "pag_0001 (3).jpg" or "pag_0001.jpg"
        match = re.match(r"(pag_\w+?)(?:\s*\(|\.jpg)", f.name, re.IGNORECASE)
        if match:
            prefix = match.group(1)
        else:
            prefix = f.stem
        groups.setdefault(prefix, []).append(f)
    return groups


def extract_page_number(prefix: str) -> int:
    """Extract numeric page from prefix like 'pag_0148'. Returns 0 for 'pag_XXXX'."""
    m = re.search(r"(\d+)", prefix)
    return int(m.group(1)) if m else 0


# ---------- batch state ----------

@dataclass
class ImageState:
    """Processing state for a single image."""
    path: str
    group: str
    status: str = "pending"  # pending, done, error
    records: int = 0
    con_dni: int = 0
    con_nombre: int = 0
    con_destino: int = 0
    calidad: str = ""
    error: str = ""
    elapsed: float = 0.0


@dataclass
class BatchState:
    """Full batch state with resume support."""
    images: dict[str, ImageState] = field(default_factory=dict)
    started_at: str = ""
    last_updated: str = ""

    def save(self, path: Path = STATE_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "started_at": self.started_at,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": len(self.images),
                "done": sum(1 for s in self.images.values() if s.status == "done"),
                "error": sum(1 for s in self.images.values() if s.status == "error"),
                "pending": sum(1 for s in self.images.values() if s.status == "pending"),
            },
            "images": {k: asdict(v) for k, v in self.images.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path = STATE_FILE) -> BatchState:
        if not path.exists():
            return cls(started_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        state = cls(started_at=data.get("started_at", ""))
        for key, val in data.get("images", {}).items():
            state.images[key] = ImageState(**val)
        return state

    def pending_in_group(self, group: str) -> list[str]:
        return [
            k for k, v in self.images.items()
            if v.group == group and v.status == "pending"
        ]


# ---------- processor ----------

def _print_state_summary(state: BatchState) -> None:
    """Print a summary of the batch state."""
    done = [s for s in state.images.values() if s.status == "done"]
    errors = [s for s in state.images.values() if s.status == "error"]
    pending = [s for s in state.images.values() if s.status == "pending"]

    total_records = sum(s.records for s in done)
    total_time = sum(s.elapsed for s in done)

    print(f"  Done: {len(done)}, Errors: {len(errors)}, Pending: {len(pending)}")
    print(f"  Total records: {total_records}")
    if done:
        print(f"  Avg records/image: {total_records / len(done):.1f}")
        print(f"  Total time: {total_time:.0f}s ({total_time / len(done):.1f}s avg)")
    print(f"{'='*60}")


class BatchProcessor:
    """Process images with Claude Vision, tracking state."""

    def __init__(self, distrito: str = "069") -> None:
        self._distrito = distrito
        self._pipeline: SingleImagePipeline | None = None

    def _get_pipeline(self, pagina: int | None = None) -> SingleImagePipeline:
        return SingleImagePipeline.with_claude(
            distrito=self._distrito, pagina=pagina
        )

    def run_sample(self, per_group: int = 2) -> None:
        """Process a sample: N images per group to validate quality."""
        groups = discover_images(IMAGE_DIR)
        state = BatchState.load()

        # Also include corrected images if available
        corrected = discover_images(CORRECTED_DIR) if CORRECTED_DIR.exists() else {}

        print(f"\n{'='*60}")
        print(f"  SAMPLE MODE — {per_group} image(s) per group")
        print(f"  Groups: {len(groups)}, Total images: {sum(len(v) for v in groups.values())}")
        print(f"{'='*60}\n")

        for prefix in sorted(groups.keys()):
            page_num = extract_page_number(prefix)
            all_images = list(groups[prefix])

            # Add corrected images for this group
            if prefix in corrected:
                all_images = list(corrected[prefix]) + all_images

            # Pick sample: prefer corrected, then base (.jpg), then variants
            sample = self._select_sample(all_images, per_group)

            print(f"\n  [{prefix}] page={page_num}, total_variants={len(all_images)}, sampling={len(sample)}")

            for img_path in sample:
                key = str(img_path)
                if key in state.images and state.images[key].status == "done":
                    s = state.images[key]
                    print(f"    SKIP (already done): {img_path.name} → {s.records} records")
                    continue

                self._process_one(img_path, prefix, page_num, state)

        state.save()
        print(f"\n{'='*60}")
        _print_state_summary(state)

    def run_full(self) -> None:
        """Process ALL images."""
        groups = discover_images(IMAGE_DIR)
        corrected = discover_images(CORRECTED_DIR) if CORRECTED_DIR.exists() else {}
        state = BatchState.load()

        total = sum(len(v) for v in groups.values()) + sum(len(v) for v in corrected.values())
        done = sum(1 for s in state.images.values() if s.status == "done")

        print(f"\n{'='*60}")
        print(f"  FULL MODE — {total} images ({done} already done)")
        print(f"{'='*60}\n")

        for prefix in sorted(groups.keys()):
            page_num = extract_page_number(prefix)
            all_images = list(groups[prefix])
            if prefix in corrected:
                all_images = list(corrected[prefix]) + all_images

            pending = [
                img for img in all_images
                if str(img) not in state.images or state.images[str(img)].status != "done"
            ]

            if not pending:
                print(f"  [{prefix}] all done ({len(all_images)} images)")
                continue

            print(f"\n  [{prefix}] page={page_num}, pending={len(pending)}/{len(all_images)}")

            for img_path in pending:
                self._process_one(img_path, prefix, page_num, state)

        state.save()
        print(f"\n{'='*60}")
        _print_state_summary(state)

    def _process_one(
        self, img_path: Path, group: str, page_num: int, state: BatchState
    ) -> None:
        """Process a single image and update state."""
        key = str(img_path)
        t0 = time.time()

        try:
            pipeline = self._get_pipeline(pagina=page_num if page_num > 0 else None)
            result = pipeline.process(str(img_path), page_num=page_num)

            elapsed = time.time() - t0
            s = result.stats

            state.images[key] = ImageState(
                path=key,
                group=group,
                status="done",
                records=s.total_records,
                con_dni=s.con_dni,
                con_nombre=s.con_nombre,
                con_destino=s.con_destino,
                calidad=result.calidad,
                elapsed=round(elapsed, 1),
            )

            # Save JSON result
            out_dir = OUTPUT_DIR / group
            out_dir.mkdir(parents=True, exist_ok=True)
            base = img_path.stem
            OutputWriter.to_json(result.records, out_dir / f"{base}.json", result)

            status_icon = "✓" if s.total_records >= ANOMALY_LOW else "⚠"
            print(
                f"    {status_icon} {img_path.name}: "
                f"{s.total_records} records, "
                f"DNI={s.con_dni}, "
                f"nombre={s.con_nombre}, "
                f"destino={s.con_destino} "
                f"[{result.calidad}] ({elapsed:.1f}s)"
            )

        except Exception as e:
            elapsed = time.time() - t0
            state.images[key] = ImageState(
                path=key,
                group=group,
                status="error",
                error=str(e),
                elapsed=round(elapsed, 1),
            )
            print(f"    ✗ {img_path.name}: ERROR — {e}")

        # Save state after each image (resume support)
        state.save()

    def _select_sample(self, images: list[Path], n: int) -> list[Path]:
        """Select N images for sampling.

        Priority: corrected > base (no parens) > first variants.
        """
        corrected = [p for p in images if "corregidas" in str(p)]
        base = [p for p in images if "(" not in p.name and "corregidas" not in str(p)]
        variants = [p for p in images if "(" in p.name and "corregidas" not in str(p)]

        selected: list[Path] = []
        for source in [corrected, base, variants]:
            for img in source:
                if len(selected) >= n:
                    break
                selected.append(img)
            if len(selected) >= n:
                break
        return selected

    def generate_report(self) -> None:
        """Generate a quality report from batch state."""
        state = BatchState.load()
        if not state.images:
            print("  No results yet. Run sample or full first.")
            return

        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("QUALITY REPORT — SUTEBA Padrón La Matanza OCR")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # Group results
        groups: dict[str, list[ImageState]] = {}
        for s in state.images.values():
            groups.setdefault(s.group, []).append(s)

        total_records = 0
        anomalies: list[str] = []

        for prefix in sorted(groups.keys()):
            items = groups[prefix]
            done = [s for s in items if s.status == "done"]
            errors = [s for s in items if s.status == "error"]

            lines.append(f"\n--- {prefix} (page {extract_page_number(prefix)}) ---")
            lines.append(f"  Processed: {len(done)}, Errors: {len(errors)}")

            if done:
                best = max(done, key=lambda s: (s.con_dni, s.con_nombre, s.records))
                lines.append(
                    f"  Best: {Path(best.path).name} → "
                    f"{best.records} records, DNI={best.con_dni}, "
                    f"nombre={best.con_nombre}, destino={best.con_destino} "
                    f"[{best.calidad}]"
                )
                total_records += best.records

                # Check anomalies
                if best.records < ANOMALY_LOW:
                    anomalies.append(f"  LOW: {prefix} → {best.records} records (< {ANOMALY_LOW})")
                elif best.records > ANOMALY_HIGH:
                    anomalies.append(f"  HIGH: {prefix} → {best.records} records (> {ANOMALY_HIGH})")

            for s in done:
                flag = " ⚠" if s.records < ANOMALY_LOW else ""
                lines.append(
                    f"    {Path(s.path).name}: {s.records} rec, "
                    f"DNI={s.con_dni}, dest={s.con_destino}, "
                    f"{s.calidad} ({s.elapsed}s){flag}"
                )

            for s in errors:
                lines.append(f"    {Path(s.path).name}: ERROR — {s.error}")

        lines.append(f"\n{'='*70}")
        lines.append(f"TOTAL (best per group): {total_records} records from {len(groups)} pages")

        if anomalies:
            lines.append(f"\nANOMALIES ({len(anomalies)}):")
            lines.extend(anomalies)
        else:
            lines.append("\nNo anomalies detected.")

        lines.append("=" * 70)

        report = "\n".join(lines)
        print(report)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  Report saved to: {REPORT_FILE}")

    def combine_best(self) -> None:
        """Select best variant per group and combine into single CSV."""
        state = BatchState.load()

        # Group done results
        groups: dict[str, list[ImageState]] = {}
        for s in state.images.values():
            if s.status == "done":
                groups.setdefault(s.group, []).append(s)

        if not groups:
            print("  No results to combine.")
            return

        all_records: list[dict] = []

        for prefix in sorted(groups.keys()):
            done = groups[prefix]
            # Best = most DNI matches, then most records
            best = max(done, key=lambda s: (s.con_dni, s.con_nombre, s.records))
            json_path = OUTPUT_DIR / prefix / f"{Path(best.path).stem}.json"

            if not json_path.exists():
                print(f"  WARNING: missing JSON for {prefix}: {json_path}")
                continue

            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            page_num = extract_page_number(prefix)
            for rec in data.get("registros", []):
                rec["pagina"] = page_num
                rec["source_file"] = Path(best.path).name
                all_records.append(rec)

            print(
                f"  {prefix}: {Path(best.path).name} → "
                f"{len(data.get('registros', []))} records"
            )

        # Write combined CSV
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(COMBINED_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["PAGINA", "TIPO", "DOCUMENTO", "NOMBRE", "DESTINO", "MESA", "CONFIANZA", "SOURCE"])
            for r in all_records:
                writer.writerow([
                    r.get("pagina", ""),
                    r.get("tipo", ""),
                    r.get("documento", ""),
                    r.get("nombre", ""),
                    r.get("destino", ""),
                    r.get("mesa", ""),
                    r.get("confianza", ""),
                    r.get("source_file", ""),
                ])

        print(f"\n  Combined: {len(all_records)} records from {len(groups)} pages")
        print(f"  Saved to: {COMBINED_CSV}")


# ---------- CLI ----------

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    processor = BatchProcessor()

    if cmd == "sample":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        processor.run_sample(per_group=n)
    elif cmd == "full":
        processor.run_full()
    elif cmd == "report":
        processor.generate_report()
    elif cmd == "combine":
        processor.combine_best()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
