"""Unit tests for preprocessing steps and pipeline."""

import numpy as np
import pytest

from ocr_engine.preprocessing.steps import (
    Binarizer,
    ClaheEnhancer,
    Deskewer,
    ExifCorrector,
    Grayscaler,
    Normalizer,
    Resizer,
    Sharpener,
    TableCropper,
    STEP_REGISTRY,
)
from ocr_engine.preprocessing.pipeline import PreprocessingPipeline


# ============================================================
# Helpers — small synthetic images
# ============================================================

@pytest.fixture
def gray_image():
    """100x100 grayscale image with some variation."""
    img = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
    return img


@pytest.fixture
def bgr_image():
    """100x100 BGR image with some variation."""
    img = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    return img


@pytest.fixture
def low_contrast_gray():
    """100x100 grayscale with very low contrast (std < 17)."""
    img = np.full((100, 100), 128, dtype=np.uint8)
    img[40:60, 40:60] = 130  # tiny variation
    return img


# ============================================================
# Individual step tests
# ============================================================

class TestExifCorrector:

    def test_passthrough(self, bgr_image):
        step = ExifCorrector()
        result = step(bgr_image)
        assert result.shape == bgr_image.shape
        np.testing.assert_array_equal(result, bgr_image)


class TestGrayscaler:

    def test_bgr_to_gray(self, bgr_image):
        step = Grayscaler()
        result = step(bgr_image)
        assert len(result.shape) == 2
        assert result.shape[:2] == bgr_image.shape[:2]

    def test_gray_passthrough(self, gray_image):
        step = Grayscaler()
        result = step(gray_image)
        assert len(result.shape) == 2
        np.testing.assert_array_equal(result, gray_image)


class TestNormalizer:

    def test_output_range(self, gray_image):
        step = Normalizer()
        result = step(gray_image)
        assert result.dtype == np.uint8
        assert result.min() == 0
        assert result.max() == 255

    def test_preserves_shape(self, bgr_image):
        step = Normalizer()
        result = step(bgr_image)
        assert result.shape == bgr_image.shape


class TestSharpener:

    def test_preserves_shape(self, gray_image):
        step = Sharpener()
        result = step(gray_image)
        assert result.shape == gray_image.shape
        assert result.dtype == np.uint8

    def test_different_output(self, gray_image):
        step = Sharpener()
        result = step(gray_image)
        # Sharpening should change pixel values
        assert not np.array_equal(result, gray_image)


class TestBinarizer:

    def test_fixed_threshold(self, gray_image):
        step = Binarizer(method="fixed", threshold=128)
        result = step(gray_image)
        assert result.shape == gray_image.shape
        unique = np.unique(result)
        assert all(v in (0, 255) for v in unique)

    def test_otsu(self, gray_image):
        step = Binarizer(method="otsu")
        result = step(gray_image)
        unique = np.unique(result)
        assert all(v in (0, 255) for v in unique)

    def test_adaptive(self, gray_image):
        step = Binarizer(method="adaptive")
        result = step(gray_image)
        unique = np.unique(result)
        assert all(v in (0, 255) for v in unique)

    def test_sauvola_fallback(self, gray_image):
        """Sauvola should work (or fall back to adaptive) without crash."""
        step = Binarizer(method="sauvola")
        result = step(gray_image)
        assert result.shape == gray_image.shape

    def test_unknown_method_raises(self, gray_image):
        step = Binarizer(method="nonexistent")
        with pytest.raises(ValueError, match="Unknown binarization"):
            step(gray_image)

    def test_bgr_input(self, bgr_image):
        step = Binarizer(method="fixed")
        result = step(bgr_image)
        assert len(result.shape) == 2  # Should convert to gray


class TestClaheEnhancer:

    def test_low_contrast_enhances(self, low_contrast_gray):
        step = ClaheEnhancer(std_threshold=17.0)
        result = step(low_contrast_gray)
        # CLAHE should increase contrast
        assert result.std() >= low_contrast_gray.std()

    def test_good_contrast_passthrough(self, gray_image):
        step = ClaheEnhancer(std_threshold=17.0)
        result = step(gray_image)
        # Good contrast image should pass through unchanged
        np.testing.assert_array_equal(result, gray_image)


class TestResizer:

    def test_resize_large(self):
        img = np.zeros((1000, 3000), dtype=np.uint8)
        step = Resizer(max_width=1500)
        result = step(img)
        assert result.shape[1] == 1500
        assert result.shape[0] == 500  # Aspect ratio preserved

    def test_small_passthrough(self, gray_image):
        step = Resizer(max_width=1500)
        result = step(gray_image)
        assert result.shape == gray_image.shape


class TestDeskewer:

    def test_no_skew(self, gray_image):
        step = Deskewer()
        result = step(gray_image)
        assert result.shape == gray_image.shape


class TestTableCropper:

    def test_crops_content(self):
        # Image with content only in center
        img = np.full((200, 200), 255, dtype=np.uint8)
        img[50:150, 50:150] = 0  # Black square in center
        # Convert to BGR for the step
        bgr = np.stack([img, img, img], axis=2)
        step = TableCropper(margin=10)
        result = step(bgr)
        # Cropped should be smaller than original
        assert result.shape[0] < bgr.shape[0]
        assert result.shape[1] < bgr.shape[1]


# ============================================================
# Step registry
# ============================================================

class TestStepRegistry:

    def test_all_steps_registered(self):
        expected = {"exif", "deskew", "crop", "grayscale", "normalize",
                    "sharpen", "binarize", "clahe", "resize"}
        assert set(STEP_REGISTRY.keys()) == expected

    def test_instantiation(self):
        for name, cls in STEP_REGISTRY.items():
            step = cls()
            assert step.name == name


# ============================================================
# Pipeline tests
# ============================================================

class TestPipeline:

    def test_default_tesseract_step_count(self):
        pipeline = PreprocessingPipeline.default_tesseract()
        assert pipeline.step_count == 6

    def test_default_vision_step_count(self):
        pipeline = PreprocessingPipeline.default_vision()
        assert pipeline.step_count == 3

    def test_fluent_api(self):
        pipeline = PreprocessingPipeline()
        result = pipeline.add(Grayscaler()).add(Normalizer())
        assert result is pipeline  # Fluent
        assert pipeline.step_count == 2

    def test_process(self, bgr_image):
        pipeline = PreprocessingPipeline()
        pipeline.add(Grayscaler()).add(Normalizer())
        result = pipeline.process(bgr_image)
        assert len(result.shape) == 2  # Grayscale
        assert result.min() == 0
        assert result.max() == 255

    def test_from_config(self):
        config = [
            {"name": "grayscale"},
            {"name": "normalize"},
            {"name": "binarize", "params": {"method": "otsu"}},
        ]
        pipeline = PreprocessingPipeline.from_config(config)
        assert pipeline.step_count == 3

    def test_from_config_invalid_step(self):
        config = [{"name": "nonexistent_step"}]
        with pytest.raises(ValueError, match="Unknown step"):
            PreprocessingPipeline.from_config(config)

    def test_default_tesseract_steps(self):
        pipeline = PreprocessingPipeline.default_tesseract()
        step_names = [s.name for s in pipeline.steps]
        assert step_names == ["crop", "deskew", "grayscale", "normalize", "sharpen", "binarize"]

    def test_default_vision_steps(self):
        pipeline = PreprocessingPipeline.default_vision()
        step_names = [s.name for s in pipeline.steps]
        assert step_names == ["grayscale", "clahe", "resize"]
