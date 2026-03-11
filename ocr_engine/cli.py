"""CLI for ocr_engine — argparse-based command line interface.

Usage:
    python -m ocr_engine image <path> -d 069
    python -m ocr_engine batch <dir> -d 069
    python -m ocr_engine vision <path> -d 069
    python -m ocr_engine --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_image(args: argparse.Namespace) -> None:
    """Process a single image."""
    from .pipeline import SingleImagePipeline
    from .output import OutputWriter

    pipeline = SingleImagePipeline.with_tesseract(
        distrito=args.distrito, psm=args.psm
    )
    result = pipeline.process(args.input, debug=args.debug)

    # Output
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = Path(args.input).stem

    if "json" in args.format:
        json_path = out_dir / f"{base}_resultado.json"
        OutputWriter.to_json(result.records, json_path, page_result=result)
        print(f"  JSON: {json_path}")

    if "csv" in args.format:
        csv_path = out_dir / f"{base}_datos.csv"
        OutputWriter.to_csv(result.records, csv_path)
        print(f"  CSV:  {csv_path}")

    if "xlsx" in args.format:
        xlsx_path = out_dir / f"{base}_datos.xlsx"
        OutputWriter.to_xlsx(result.records, xlsx_path)
        print(f"  XLSX: {xlsx_path}")

    _print_summary(result)


def cmd_batch(args: argparse.Namespace) -> None:
    """Process all images in a directory."""
    from .pipeline import SingleImagePipeline
    from .output import OutputWriter

    input_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    images = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in extensions)

    if not images:
        print(f"  No images found in {input_dir}")
        sys.exit(1)

    pipeline = SingleImagePipeline.with_tesseract(
        distrito=args.distrito, psm=args.psm
    )

    total_records = 0
    for img_path in images:
        print(f"\n  Processing: {img_path.name}")
        result = pipeline.process(str(img_path), debug=args.debug)
        total_records += len(result.records)

        base = img_path.stem
        if "json" in args.format:
            OutputWriter.to_json(result.records, out_dir / f"{base}_resultado.json", result)
        if "csv" in args.format:
            OutputWriter.to_csv(result.records, out_dir / f"{base}_datos.csv")

        _print_summary(result, indent=4)

    print(f"\n  Total: {total_records} records from {len(images)} images")


def cmd_vision(args: argparse.Namespace) -> None:
    """Process images using Claude Vision."""
    from .pipeline import SingleImagePipeline
    from .output import OutputWriter

    pipeline = SingleImagePipeline.with_claude(
        distrito=args.distrito, pagina=args.pagina
    )

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = Path(args.input).stem

    result = pipeline.process(args.input, page_num=args.pagina or 0, debug=args.debug)

    if "json" in args.format:
        json_path = out_dir / f"{base}_resultado.json"
        OutputWriter.to_json(result.records, json_path, page_result=result)
        print(f"  JSON: {json_path}")

    _print_summary(result)


def cmd_google(args: argparse.Namespace) -> None:
    """Process images using Google Cloud Vision."""
    from .pipeline import SingleImagePipeline
    from .output import OutputWriter

    pipeline = SingleImagePipeline.with_google(distrito=args.distrito)

    input_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Single file or directory (batch)
    if input_path.is_file():
        images = [input_path]
    elif input_path.is_dir():
        extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
        images = sorted(f for f in input_path.iterdir() if f.suffix.lower() in extensions)
    else:
        print(f"  Error: {input_path} not found")
        sys.exit(1)

    if not images:
        print(f"  No images found in {input_path}")
        sys.exit(1)

    print(f"  Google Vision — Processing {len(images)} image(s)")
    total_records = 0

    for i, img_path in enumerate(images, 1):
        print(f"\n  [{i}/{len(images)}] {img_path.name}")
        try:
            result = pipeline.process(str(img_path), debug=args.debug)
            total_records += len(result.records)

            base = img_path.stem
            if "json" in args.format:
                OutputWriter.to_json(result.records, out_dir / f"{base}_resultado.json", result)
            if "csv" in args.format:
                OutputWriter.to_csv(result.records, out_dir / f"{base}_datos.csv")
            if "xlsx" in args.format:
                OutputWriter.to_xlsx(result.records, out_dir / f"{base}_datos.xlsx")

            _print_summary(result, indent=4)
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\n  Total: {total_records} records from {len(images)} images")


def _print_summary(result, indent: int = 2) -> None:
    """Print a summary of processing results."""
    pad = " " * indent
    s = result.stats
    print(f"{pad}Records: {s.total_records}/{s.filas_esperadas} ({s.completitud}%)")
    print(f"{pad}DNI: {s.con_dni}  Nombre: {s.con_nombre}  Destino: {s.con_destino}")
    print(f"{pad}Calidad: {result.calidad}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="ocr_engine",
        description="OCR Engine — Unified OCR for SUTEBA padron processing",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments
    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("-d", "--distrito", default="069", help="Distrito code (default: 069)")
        sub.add_argument("-o", "--output", default="./output", help="Output directory")
        sub.add_argument(
            "-f", "--format", nargs="+", default=["json"],
            choices=["json", "csv", "xlsx"], help="Output formats",
        )
        sub.add_argument("--debug", action="store_true", help="Save debug images")
        sub.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # image subcommand
    image_parser = subparsers.add_parser("image", help="Process a single image")
    image_parser.add_argument("input", help="Path to image file")
    image_parser.add_argument("--psm", type=int, default=4, help="Tesseract PSM mode (default: 4)")
    add_common(image_parser)

    # batch subcommand
    batch_parser = subparsers.add_parser("batch", help="Process all images in a directory")
    batch_parser.add_argument("input", help="Directory with images")
    batch_parser.add_argument("--psm", type=int, default=4, help="Tesseract PSM mode (default: 4)")
    add_common(batch_parser)

    # vision subcommand
    vision_parser = subparsers.add_parser("vision", help="Process with Claude Vision")
    vision_parser.add_argument("input", help="Path to image file")
    vision_parser.add_argument("--pagina", type=int, default=None, help="Known page number")
    add_common(vision_parser)

    # google subcommand
    google_parser = subparsers.add_parser("google", help="Process with Google Cloud Vision")
    google_parser.add_argument("input", help="Path to image file or directory")
    add_common(google_parser)

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "image": cmd_image,
        "batch": cmd_batch,
        "vision": cmd_vision,
        "google": cmd_google,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
