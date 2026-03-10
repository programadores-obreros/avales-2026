"""Abstract base class for OCR engines and factory registry."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .models import OcrResult


class OcrEngine(ABC):
    """Abstract base class for all OCR engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine identifier (e.g. 'tesseract', 'paddle', 'claude')."""
        ...

    @abstractmethod
    def recognize(self, image: np.ndarray) -> OcrResult:
        """Run OCR on a preprocessed image.

        Args:
            image: OpenCV image (BGR or grayscale numpy array).

        Returns:
            OcrResult with raw text, parsed lines, and confidence.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this engine is installed and ready to use."""
        ...


class EngineFactory:
    """Registry and factory for OCR engines."""

    _registry: dict[str, type[OcrEngine]] = {}

    @classmethod
    def register(cls, name: str, engine_class: type[OcrEngine]) -> None:
        """Register an engine class by name."""
        cls._registry[name] = engine_class

    @classmethod
    def create(cls, name: str, **kwargs) -> OcrEngine:
        """Create an engine instance by name.

        Args:
            name: Registered engine name.
            **kwargs: Arguments passed to the engine constructor.

        Raises:
            KeyError: If engine name is not registered.
        """
        if name not in cls._registry:
            available = ", ".join(cls._registry.keys()) or "(none)"
            raise KeyError(f"Engine '{name}' not registered. Available: {available}")
        return cls._registry[name](**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        """Return names of registered engines that are available."""
        result = []
        for name, engine_class in cls._registry.items():
            try:
                instance = engine_class()
                if instance.is_available():
                    result.append(name)
            except Exception:
                pass
        return result

    @classmethod
    def registered(cls) -> list[str]:
        """Return all registered engine names (whether available or not)."""
        return list(cls._registry.keys())
