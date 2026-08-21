import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

# First bytes of any valid PDF. Checked in addition to the client-supplied
# content-type/extension, since both of those are trivially spoofable.
PDF_MAGIC = b"%PDF-"
ALLOWED_CONTENT_TYPES = {"application/pdf"}

_CHUNK_SIZE = 1024 * 1024


class ResumeUploadError(ValueError):
    """Raised when an uploaded resume fails validation. Message is user-facing."""


def _upload_dir() -> Path:
    upload_dir = Path(settings.resume_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def validate_and_read(file: UploadFile) -> bytes:
    """Validate content-type, extension, size, and magic bytes; return the bytes.

    Reads in bounded chunks so an oversized upload is rejected without ever
    buffering more than resume_max_size_bytes (+ one chunk) into memory.
    Raises ResumeUploadError with a message safe to show the client.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ResumeUploadError("Only PDF files are supported.")

    if not (file.filename or "").lower().endswith(".pdf"):
        raise ResumeUploadError("Only .pdf files are supported.")

    max_size = settings.resume_max_size_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise ResumeUploadError(
                f"Resume exceeds the {max_size // (1024 * 1024)}MB size limit."
            )
        chunks.append(chunk)

    data = b"".join(chunks)
    if not data:
        raise ResumeUploadError("Uploaded file is empty.")
    if not data.startswith(PDF_MAGIC):
        raise ResumeUploadError("File does not look like a valid PDF.")

    return data


def save_resume_file(data: bytes) -> str:
    """Persist resume bytes under a generated filename and return that filename.

    The stored filename is never derived from client input (original filename
    is kept only as metadata), which rules out path traversal / overwrite
    regardless of what the client sends. This directory is never mounted as
    static files, so saved resumes have no public URL.
    """
    stored_filename = f"{uuid.uuid4().hex}.pdf"
    path = _upload_dir() / stored_filename
    path.write_bytes(data)
    return stored_filename
