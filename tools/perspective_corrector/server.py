#!/usr/bin/env python3
"""Perspective Correction Tool — Local web tool for manual 4-point correction.

Usage:
    python server.py <input_dir> [-o <output_dir>] [-p 8080]

Opens a web interface where you:
1. View each image
2. Click 4 corners of the page/table
3. Preview the perspective-corrected result
4. Save and move to the next image
"""

from __future__ import annotations

import argparse
import base64
import http.server
import json
import mimetypes
import socketserver
import urllib.parse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    d = np.diff(pts, axis=1).ravel()
    rect[1] = pts[np.argmin(d)]
    rect[3] = pts[np.argmax(d)]
    return rect


def apply_perspective(img: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Apply perspective correction using 4 corner points."""
    pts = order_points(points)

    width_top = np.linalg.norm(pts[1] - pts[0])
    width_bottom = np.linalg.norm(pts[2] - pts[3])
    width = int(max(width_top, width_bottom))

    height_left = np.linalg.norm(pts[3] - pts[0])
    height_right = np.linalg.norm(pts[2] - pts[1])
    height = int(max(height_left, height_right))

    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(pts, dst)
    return cv2.warpPerspective(img, M, (width, height))


def load_image(path: str) -> np.ndarray:
    """Load image with EXIF orientation correction."""
    pil_img = Image.open(path)
    pil_img = ImageOps.exif_transpose(pil_img)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def make_handler(input_dir: Path, output_dir: Path, tool_dir: Path):
    """Create the HTTP handler class with the given directories."""

    class Handler(http.server.BaseHTTPRequestHandler):

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path in ("/", "/index.html"):
                self._serve_file(tool_dir / "index.html", "text/html; charset=utf-8")
            elif path == "/api/images":
                self._api_list_images()
            elif path.startswith("/images/"):
                name = urllib.parse.unquote(path[8:])
                self._serve_file(input_dir / name)
            elif path.startswith("/output/"):
                name = urllib.parse.unquote(path[8:])
                self._serve_file(output_dir / name)
            else:
                self.send_error(404)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            data = json.loads(body)

            if path == "/api/preview":
                self._api_preview(data)
            elif path == "/api/save":
                self._api_save(data)
            else:
                self.send_error(404)

        def _serve_file(self, filepath: Path, content_type: str | None = None):
            if not filepath.exists():
                self.send_error(404)
                return
            data = filepath.read_bytes()
            if content_type is None:
                content_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(data))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)

        def _api_list_images(self):
            images = sorted(
                f.name for f in input_dir.iterdir() if f.suffix.lower() in EXTENSIONS
            )
            processed = set()
            if output_dir.exists():
                processed = {
                    f.name for f in output_dir.iterdir() if f.suffix.lower() in EXTENSIONS
                }
            result = [{"name": n, "processed": n in processed} for n in images]
            self._json_response(result)

        def _api_preview(self, data: dict):
            name = data["image"]
            points = np.array(data["points"], dtype=np.float32)

            img_path = input_dir / name
            if not img_path.exists():
                self.send_error(404, f"Image not found: {name}")
                return

            img = load_image(str(img_path))
            corrected = apply_perspective(img, points)

            _, buf = cv2.imencode(".jpg", corrected, [cv2.IMWRITE_JPEG_QUALITY, 90])
            b64 = base64.b64encode(buf).decode()

            self._json_response({
                "preview": f"data:image/jpeg;base64,{b64}",
                "size": [corrected.shape[1], corrected.shape[0]],
            })

        def _api_save(self, data: dict):
            name = data["image"]
            points = np.array(data["points"], dtype=np.float32)

            img_path = input_dir / name
            if not img_path.exists():
                self.send_error(404, f"Image not found: {name}")
                return

            output_dir.mkdir(parents=True, exist_ok=True)
            img = load_image(str(img_path))
            corrected = apply_perspective(img, points)

            out_path = output_dir / name
            cv2.imwrite(str(out_path), corrected, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Count processed
            processed = sum(
                1 for f in output_dir.iterdir() if f.suffix.lower() in EXTENSIONS
            )
            total = sum(
                1 for f in input_dir.iterdir() if f.suffix.lower() in EXTENSIONS
            )
            self._json_response({
                "saved": str(out_path),
                "processed": processed,
                "total": total,
            })

        def _json_response(self, data: dict | list):
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            # Only log errors, not every request
            if args and str(args[0]).startswith("4"):
                super().log_message(fmt, *args)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Perspective Correction Tool")
    parser.add_argument("input_dir", help="Directory with images to correct")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: <input_dir>_corregidas)")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Server port (default: 8080)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory")
        return

    output_dir = Path(args.output).resolve() if args.output else input_dir.parent / f"{input_dir.name}_corregidas"
    tool_dir = Path(__file__).parent.resolve()

    n_images = sum(1 for f in input_dir.iterdir() if f.suffix.lower() in EXTENSIONS)
    n_done = sum(1 for f in output_dir.iterdir() if f.suffix.lower() in EXTENSIONS) if output_dir.exists() else 0

    print(f"  Perspective Corrector")
    print(f"  Input:  {input_dir} ({n_images} images)")
    print(f"  Output: {output_dir} ({n_done} already processed)")
    print(f"  URL:    http://localhost:{args.port}")
    print()

    handler = make_handler(input_dir, output_dir, tool_dir)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", args.port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")


if __name__ == "__main__":
    main()
