"""Extraction and normalization package."""

from core.models import FOARecord
from core.normalization import FOANormalizer
from .pdf_extractor import extract_text_from_pdf

__all__ = ["FOANormalizer", "FOARecord", "extract_text_from_pdf"]
