"""Individual preprocessing step implementations.

Each step is a callable: __call__(img: np.ndarray) -> np.ndarray.
Extracted from procesar_padron.py and procesar_preparadas.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import cv2
import numpy as np
from PIL import Image, ImageOps


class PreprocessingStep(ABC):
    """Base class for all preprocessing steps."""

    name: str = "base"

    @abstractmethod
    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Apply this preprocessing step to an image.

        Args:
            img: OpenCV image (BGR or grayscale numpy array).

        Returns:
            Processed image.
        """
        ...


class ExifCorrector(PreprocessingStep):
    """Correct image orientation from EXIF metadata.

    Extracted from procesar_padron.py:corregir_exif().
    Works on file paths, not in-memory arrays (needs original EXIF).
    When called with a numpy array, returns it unchanged (EXIF already lost).
    """

    name = "exif"

    def __call__(self, img: np.ndarray) -> np.ndarray:
        # EXIF is only in the original file — once we have a numpy array,
        # orientation has already been applied or lost.
        return img

    @staticmethod
    def from_file(path: str) -> np.ndarray:
        """Load an image file with EXIF orientation correction.

        Args:
            path: Path to the image file.

        Returns:
            OpenCV BGR image with correct orientation.
        """
        pil_img = Image.open(path)
        pil_img = ImageOps.exif_transpose(pil_img)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


class Deskewer(PreprocessingStep):
    """Correct image skew using minAreaRect.

    Extracted from procesar_padron.py:enderezar().
    """

    name = "deskew"

    def __init__(self, max_angle: float = 10.0, min_angle: float = 0.2) -> None:
        self._max_angle = max_angle
        self._min_angle = min_angle

    def __call__(self, img: np.ndarray) -> np.ndarray:
        from .deskew import deskew_image

        corrected, _angle = deskew_image(
            img, max_angle=self._max_angle, min_angle=self._min_angle
        )
        return corrected


class TableCropper(PreprocessingStep):
    """Crop image to the table content area.

    Extracted from procesar_padron.py:detectar_y_recortar_tabla().
    """

    name = "crop"

    def __init__(self, margin: int = 20) -> None:
        self._margin = margin

    def __call__(self, img: np.ndarray) -> np.ndarray:
        from .crop import crop_table

        return crop_table(img, margin=self._margin)


class Grayscaler(PreprocessingStep):
    """Convert BGR image to grayscale."""

    name = "grayscale"

    def __call__(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img


class Normalizer(PreprocessingStep):
    """Normalize image intensity range.

    Replaces ImageMagick's `-normalize` command.
    Uses OpenCV's NORM_MINMAX to stretch histogram to full [0, 255].
    """

    name = "normalize"

    def __call__(self, img: np.ndarray) -> np.ndarray:
        return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)


class Sharpener(PreprocessingStep):
    """Sharpen image using Gaussian blur subtraction.

    Replaces ImageMagick's `-unsharp 6x3+3+0`.
    The unsharp mask: output = original + amount * (original - blurred)
    """

    name = "sharpen"

    def __init__(self, kernel_size: int = 7, sigma: float = 3.0, amount: float = 3.0) -> None:
        self._kernel_size = kernel_size
        self._sigma = sigma
        self._amount = amount

    def __call__(self, img: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(img, (self._kernel_size, self._kernel_size), self._sigma)
        sharpened = cv2.addWeighted(img, 1.0 + self._amount, blurred, -self._amount, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)


class Binarizer(PreprocessingStep):
    """Binarize image using various thresholding methods.

    Methods:
        - "fixed": Fixed threshold (default, replaces magick -threshold 40%)
        - "otsu": Otsu's automatic thresholding
        - "adaptive": Adaptive mean thresholding
        - "sauvola": Sauvola local thresholding (requires opencv-contrib)
    """

    name = "binarize"

    def __init__(
        self,
        method: str = "fixed",
        threshold: int = 102,  # 40% of 255
        block_size: int = 25,
        c: int = 10,
        k: float = 0.2,
    ) -> None:
        self._method = method
        self._threshold = threshold
        self._block_size = block_size
        self._c = c
        self._k = k

    def __call__(self, img: np.ndarray) -> np.ndarray:
        # Ensure grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        if self._method == "fixed":
            _, result = cv2.threshold(gray, self._threshold, 255, cv2.THRESH_BINARY)
        elif self._method == "otsu":
            _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif self._method == "adaptive":
            result = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,
                self._block_size, self._c,
            )
        elif self._method == "sauvola":
            result = self._sauvola(gray)
        else:
            raise ValueError(f"Unknown binarization method: {self._method}")

        return result

    def _sauvola(self, gray: np.ndarray) -> np.ndarray:
        """Sauvola thresholding. Falls back to adaptive if ximgproc unavailable."""
        try:
            result = cv2.ximgproc.niBlackThreshold(
                gray, 255, cv2.THRESH_BINARY,
                self._block_size, self._k,
                binarizationMethod=cv2.ximgproc.BINARIZATION_SAUVOLA,
            )
            return result
        except AttributeError:
            # opencv-contrib not installed, fall back to adaptive
            return cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,
                self._block_size, self._c,
            )


class ClaheEnhancer(PreprocessingStep):
    """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Extracted from procesar_preparadas.py:_preprocess_for_vision().
    Applied when image has low contrast (std < threshold).
    """

    name = "clahe"

    def __init__(
        self, clip_limit: float = 2.0, tile_size: int = 8, std_threshold: float = 17.0
    ) -> None:
        self._clip_limit = clip_limit
        self._tile_size = tile_size
        self._std_threshold = std_threshold

    def __call__(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        if gray.std() < self._std_threshold:
            clahe = cv2.createCLAHE(
                clipLimit=self._clip_limit, tileGridSize=(self._tile_size, self._tile_size)
            )
            return clahe.apply(gray)
        return gray


class Resizer(PreprocessingStep):
    """Resize image to a maximum width, preserving aspect ratio.

    Extracted from procesar_preparadas.py:_preprocess_for_vision().
    """

    name = "resize"

    def __init__(self, max_width: int = 1500) -> None:
        self._max_width = max_width

    def __call__(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        if w > self._max_width:
            scale = self._max_width / w
            new_size = (self._max_width, int(h * scale))
            return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
        return img


# Step registry: name -> class
STEP_REGISTRY: dict[str, type[PreprocessingStep]] = {
    "exif": ExifCorrector,
    "deskew": Deskewer,
    "crop": TableCropper,
    "grayscale": Grayscaler,
    "normalize": Normalizer,
    "sharpen": Sharpener,
    "binarize": Binarizer,
    "clahe": ClaheEnhancer,
    "resize": Resizer,
}
