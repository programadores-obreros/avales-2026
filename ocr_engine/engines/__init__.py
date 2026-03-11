"""OCR engine implementations."""

# Import engines to trigger EngineFactory.register() calls
from . import tesseract as _tesseract  # noqa: F401
from . import claude as _claude  # noqa: F401
from . import paddle as _paddle  # noqa: F401
from . import google_vision as _google_vision  # noqa: F401
