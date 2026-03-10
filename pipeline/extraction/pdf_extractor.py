"""PDF to text extraction helpers."""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from in-memory PDF bytes with graceful fallbacks."""
    if not pdf_bytes:
        return ""

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception as exc:
        logger.debug("pypdf extraction failed: %s", exc)

    try:
        from pdfminer.high_level import extract_text

        text = extract_text(io.BytesIO(pdf_bytes))
        return (text or "").strip()
    except Exception as exc:
        logger.warning("pdfminer extraction failed: %s", exc)

    return ""
