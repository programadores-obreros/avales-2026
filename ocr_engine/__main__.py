"""Entry point for `python -m ocr_engine`."""

import sys


def main() -> None:
    print("OCR Engine — Unified OCR for SUTEBA padron processing")
    print()
    print("Usage:")
    print("  python -m ocr_engine image   <image.jpg>  [-d DISTRITO] [-e ENGINE]")
    print("  python -m ocr_engine batch   <folder/>    [-d DISTRITO] [-e ENGINE]")
    print("  python -m ocr_engine pdf     <file.pdf>   [-d DISTRITO] [--pages 1-5]")
    print("  python -m ocr_engine vision  <folder/>    [-d DISTRITO]")
    print("  python -m ocr_engine benchmark <image.jpg> [-d DISTRITO]")
    print()
    print("Options:")
    print("  -d, --distrito   Distrito code (e.g. 069 for La Matanza)")
    print("  -e, --engine     OCR engine: tesseract, paddle, claude (default: tesseract)")
    print("  -o, --output     Output directory (default: ./output)")
    print("  -f, --format     Output format: json, csv, xlsx (default: json,csv)")
    print("  --debug          Save intermediate preprocessing images")
    print("  -v, --verbose    Verbose output")


if __name__ == "__main__":
    main()
