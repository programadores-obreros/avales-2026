"""Claude Vision OCR engine implementation."""

from __future__ import annotations

import base64
import json
import os
import re
import time

import numpy as np

from ..engine import EngineFactory, OcrEngine
from ..models import OcrLine, OcrResult

VISION_PROMPT = """\
Extraé datos de una página fotografiada de un padrón sindical de SUTEBA 2026.
La imagen contiene UNA tabla principal con filas de personas.

{page_instruction}

ESTRUCTURA DE CADA FILA (4 columnas):
1. TIPO: "DNI", "LC" o "LE" (generalmente "DNI")
2. DOCUMENTO: número de 7 u 8 dígitos, sin puntos
3. APELLIDO Y NOMBRE: texto en MAYUSCULAS
4. ESCUELA/DESTINO: código con formato 0-069-XX-XXXX, o "JUBILADO/A", o "AP. EN SEDE"

REGLAS DE INTERPRETACION:
- tipo: si no se lee bien, usá "DNI" como default
- documento: SOLO dígitos, 7 u 8. Si no se lee bien, dejá ""
- nombre: transcribí EXACTO como aparece, en MAYUSCULAS. NO corrijas ortografía
- destino: código 0-069-XX-XXXX, o "JUBILADO/A", o "AP. EN SEDE", o "" si no se lee

INSTRUCCIONES IMPORTANTES:
- Extraé TODAS las filas visibles, no te saltees ninguna
- Si un campo no se lee, dejalo vacío ""
- NO completes información por contexto o inferencia
- Incluí filas aunque tengan campos ilegibles
- Ignorá encabezados de columna

SALIDA: Respondé SOLO con un JSON object, sin markdown, sin backticks:
{{"pagina": 148, "registros": [{{"tipo": "DNI", "documento": "12345678", \
"nombre": "APELLIDO NOMBRE", "destino": "0-069-MS-0001"}}]}}"""

PAGE_INSTRUCTION_AUTO = (
    "Necesito que leas el número de página visible en la hoja "
    "(suele estar abajo a la derecha)."
)
PAGE_INSTRUCTION_KNOWN = "El número de página es {pagina}."


class ClaudeVisionEngine(OcrEngine):
    """OCR engine using Claude Vision API.

    Extracted from 13_mayo_2026/padron_provisorio/procesar_preparadas.py.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        pagina: int | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._pagina = pagina
        self._last_call_time = 0.0
        self._max_retries = 3

    @property
    def name(self) -> str:
        return "claude"

    def recognize(self, image: np.ndarray) -> OcrResult:
        """Run Claude Vision OCR on a preprocessed image.

        Args:
            image: OpenCV image (grayscale or BGR numpy array).

        Returns:
            OcrResult with raw text (JSON), parsed lines, and confidence.
        """
        import anthropic

        # Rate limiting: ensure at least 1s between calls
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        # Encode image to base64 JPEG
        import cv2

        success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not success:
            raise RuntimeError("Failed to encode image to JPEG")
        img_b64 = base64.standard_b64encode(buffer).decode("utf-8")

        # Build prompt
        if self._pagina and self._pagina > 0:
            page_inst = PAGE_INSTRUCTION_KNOWN.format(pagina=self._pagina)
        else:
            page_inst = PAGE_INSTRUCTION_AUTO

        prompt = VISION_PROMPT.format(page_instruction=page_inst)

        # Call Claude with retry
        client = anthropic.Anthropic()
        raw_text = ""

        for attempt in range(self._max_retries):
            try:
                response = client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": img_b64,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                )
                raw_text = response.content[0].text.strip()
                self._last_call_time = time.time()
                break
            except anthropic.RateLimitError:
                if attempt < self._max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                else:
                    raise

        # Clean markdown backticks if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```\w*\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)
            raw_text = raw_text.strip()

        # Parse JSON response into OcrLines and text-formatted raw_text
        lines: list[OcrLine] = []
        text_lines: list[str] = []
        try:
            data = json.loads(raw_text)
            registros = data.get("registros", [])
            for r in registros:
                parts = []
                tipo = str(r.get("tipo", "DNI")).strip().upper()
                doc = re.sub(r"[^\d]", "", str(r.get("documento", "")))
                nombre = str(r.get("nombre", "")).strip().upper()
                destino = str(r.get("destino", "")).strip().upper()

                if tipo:
                    parts.append(tipo)
                if doc:
                    parts.append(doc)
                if nombre:
                    parts.append(nombre)
                if destino:
                    parts.append(destino)

                line_text = " ".join(parts)
                if line_text:
                    lines.append(OcrLine(text=line_text, confidence=0.9))
                    text_lines.append(line_text)
        except (json.JSONDecodeError, KeyError):
            # If JSON parsing fails, return raw text as lines
            for line_text in raw_text.split("\n"):
                stripped = line_text.strip()
                if stripped:
                    lines.append(OcrLine(text=stripped))
                    text_lines.append(stripped)

        # Use text-formatted lines as raw_text so the parser can handle it
        formatted_text = "\n".join(text_lines)

        return OcrResult(
            raw_text=formatted_text,
            lines=lines,
            confidence=0.9 if lines else 0.0,
            engine_name=self.name,
            metadata={"model": self._model, "pagina": self._pagina},
        )

    def is_available(self) -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401

            return True
        except ImportError:
            return False


EngineFactory.register("claude", ClaudeVisionEngine)
