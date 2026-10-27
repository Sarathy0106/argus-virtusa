"""
Circular upload + text extraction (B3).

Accepts PDF, Markdown or plain-text uploads and extracts clean text. PDF text is
extracted with pdfplumber. The extracted text is handed to the same intake
Airlock + clause chunker the preset path uses, so an uploaded PDF and its
Markdown twin produce identical clause IDs.
"""

from __future__ import annotations

import io

try:
    import pdfplumber

    _HAS_PDF = True
except Exception:  # pragma: no cover - pdfplumber optional at runtime
    _HAS_PDF = False


class UnsupportedUploadError(Exception):
    pass


def extract_text(filename: str, content: bytes) -> str:
    """Return UTF-8 text extracted from an uploaded circular."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        if not _HAS_PDF:
            raise UnsupportedUploadError("pdfplumber is not installed; cannot read PDF.")
        return _extract_pdf(content)
    if name.endswith((".md", ".markdown", ".txt", ".text")) or not name:
        return content.decode("utf-8", errors="replace")
    raise UnsupportedUploadError(f"Unsupported file type: {filename}")


def _extract_pdf(content: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parts.append(text)
    return "\n".join(parts)
