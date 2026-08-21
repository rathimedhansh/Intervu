import logging
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings

logger = logging.getLogger(__name__)


class PdfExtractionError(ValueError):
    """Raised when text can't be extracted from an uploaded PDF. Message is user-facing."""


def extract_text_from_pdf(data: bytes) -> str:
    """Extract plain text from PDF bytes.

    Bounded to settings.resume_max_pages / resume_max_text_chars so a
    pathological PDF (huge page count, decompression bomb) can't be used to
    tie up the server or blow up storage from a single upload.
    """
    try:
        reader = PdfReader(BytesIO(data))
    except PdfReadError as exc:
        raise PdfExtractionError("Could not read this PDF — it may be corrupted.") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise PdfExtractionError("This PDF is password-protected.") from exc

    pages = reader.pages[: settings.resume_max_pages]
    text_parts: list[str] = []
    for page in pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            logger.exception("Failed to extract text from a resume page; skipping it.")

    text = "\n".join(text_parts).strip()
    if not text:
        raise PdfExtractionError(
            "No extractable text found in this PDF (it may be a scanned image)."
        )

    return text[: settings.resume_max_text_chars]
