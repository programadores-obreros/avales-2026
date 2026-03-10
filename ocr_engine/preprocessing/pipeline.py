"""Preprocessing pipeline — chains steps together.

Usage:
    pipeline = PreprocessingPipeline.default_tesseract()
    processed = pipeline.process(image)
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from .steps import (
    Binarizer,
    ClaheEnhancer,
    Deskewer,
    Grayscaler,
    Normalizer,
    PreprocessingStep,
    Resizer,
    Sharpener,
    TableCropper,
    STEP_REGISTRY,
)


class PreprocessingPipeline:
    """Chains multiple preprocessing steps and applies them in order.

    Usage:
        pipeline = PreprocessingPipeline()
        pipeline.add(Grayscaler()).add(Normalizer()).add(Binarizer())
        result = pipeline.process(image)
    """

    def __init__(self) -> None:
        self._steps: list[PreprocessingStep] = []

    def add(self, step: PreprocessingStep) -> PreprocessingPipeline:
        """Add a step to the pipeline. Fluent API."""
        self._steps.append(step)
        return self

    @property
    def steps(self) -> list[PreprocessingStep]:
        return list(self._steps)

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def process(self, image: np.ndarray, debug: bool = False) -> np.ndarray:
        """Run all steps on the image in order.

        Args:
            image: Input OpenCV image.
            debug: If True, save intermediate images to /tmp/ocr_debug/.

        Returns:
            Processed image.
        """
        result = image

        if debug:
            debug_dir = Path("/tmp/ocr_debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_dir / "00_input.png"), result)

        for i, step in enumerate(self._steps):
            result = step(result)
            if debug:
                cv2.imwrite(str(debug_dir / f"{i + 1:02d}_{step.name}.png"), result)

        return result

    @classmethod
    def from_config(cls, config: list[dict]) -> PreprocessingPipeline:
        """Build a pipeline from a config list.

        Each dict should have a "name" key matching STEP_REGISTRY,
        and optional "params" dict with constructor kwargs.

        Example:
            config = [
                {"name": "crop", "params": {"margin": 30}},
                {"name": "deskew"},
                {"name": "grayscale"},
                {"name": "normalize"},
                {"name": "sharpen"},
                {"name": "binarize", "params": {"method": "otsu"}},
            ]
        """
        pipeline = cls()
        for step_config in config:
            step_name = step_config["name"]
            params = step_config.get("params", {})
            if step_name not in STEP_REGISTRY:
                available = ", ".join(STEP_REGISTRY.keys())
                raise ValueError(f"Unknown step '{step_name}'. Available: {available}")
            step_class = STEP_REGISTRY[step_name]
            pipeline.add(step_class(**params))
        return pipeline

    @classmethod
    def default_tesseract(cls) -> PreprocessingPipeline:
        """Default pipeline for Tesseract OCR.

        Mirrors the original procesar_padron.py flow:
        EXIF → crop → deskew → grayscale → normalize → sharpen → binarize
        (EXIF handled at load time, so 6 in-memory steps)
        """
        return (
            cls()
            .add(TableCropper())
            .add(Deskewer())
            .add(Grayscaler())
            .add(Normalizer())
            .add(Sharpener())
            .add(Binarizer(method="fixed"))
        )

    @classmethod
    def default_vision(cls) -> PreprocessingPipeline:
        """Default pipeline for Claude Vision.

        Lighter preprocessing — Vision models handle noise well.
        Mirrors procesar_preparadas.py flow.
        """
        return (
            cls()
            .add(Grayscaler())
            .add(ClaheEnhancer())
            .add(Resizer(max_width=1500))
        )
