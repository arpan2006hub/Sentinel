"""Bounded, optional Tesseract OCR for individual PDF pages.

The Python packages are installed from ``requirements-ocr.txt``. The Tesseract
binary and language data are installed separately by the operator. Nothing in
this module downloads executables or model data automatically.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

MAX_PAGE_PIXELS = 20_000_000
DEFAULT_DPI = 180
DEFAULT_TIMEOUT_SECONDS = 30


def _positive_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def extract_pdf_page_text(
    pdf_path: Path,
    page_index: int,
) -> tuple[str, dict[str, Any]]:
    """Render and OCR one zero-based PDF page.

    Rendering resolution and pixel count are capped to limit memory use. A
    timeout is applied to each Tesseract invocation. Raises ``RuntimeError``
    with an actionable message when the optional Python packages, Tesseract
    executable, or requested language data are unavailable.
    """
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "Scanned PDF OCR requires the optional dependencies. Run "
            "'python -m pip install -r requirements-ocr.txt'."
        ) from exc

    executable = os.getenv("TESSERACT_CMD", "").strip()
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable

    language = os.getenv("PDF_OCR_LANG", "eng").strip() or "eng"
    dpi = _positive_int_env("PDF_OCR_DPI", DEFAULT_DPI, minimum=100, maximum=300)
    timeout = _positive_int_env(
        "PDF_OCR_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, minimum=5, maximum=120
    )

    try:
        # Fail early with a clear error instead of a cryptic subprocess traceback.
        pytesseract.get_tesseract_version()
    except Exception as exc:  # TesseractNotFoundError / executable failure
        raise RuntimeError(
            "Tesseract OCR executable was not found. Install Tesseract and add it "
            "to PATH, or set TESSERACT_CMD in .env to the full tesseract.exe path."
        ) from exc

    document = None
    page = None
    bitmap = None
    image = None
    try:
        document = pdfium.PdfDocument(str(pdf_path))
        if page_index < 0 or page_index >= len(document):
            raise ValueError(f"PDF page index {page_index} is out of range")
        page = document[page_index]
        width_points, height_points = page.get_size()
        if not math.isfinite(width_points) or not math.isfinite(height_points):
            raise RuntimeError("PDF page has invalid dimensions and cannot be OCR-rendered")
        if width_points <= 0 or height_points <= 0:
            raise RuntimeError("PDF page has invalid dimensions and cannot be OCR-rendered")

        scale = dpi / 72.0
        estimated_pixels = width_points * height_points * scale * scale
        if estimated_pixels > MAX_PAGE_PIXELS:
            scale *= math.sqrt(MAX_PAGE_PIXELS / estimated_pixels)

        bitmap = page.render(scale=scale, rev_byteorder=True, prefer_bgrx=False)
        image = bitmap.to_pil()
        config = "--oem 3 --psm 6"
        text = pytesseract.image_to_string(
            image,
            lang=language,
            config=config,
            timeout=timeout,
        ).strip()
        return text, {
            "extraction_method": "tesseract_ocr",
            "ocr_engine": "tesseract",
            "ocr_language": language,
            "ocr_dpi": dpi,
            "ocr_timeout_seconds": timeout,
        }
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Tesseract could not OCR PDF page {page_index + 1}: {exc}") from exc
    finally:
        if image is not None:
            image.close()
        if bitmap is not None:
            bitmap.close()
        if page is not None:
            page.close()
        if document is not None:
            document.close()
