"""Compatibility bridge to the new core normalization layer."""

from core.models import FOARecord, SCHEMA_VERSION
from core.normalization import FOANormalizer

__all__ = ["FOARecord", "FOANormalizer", "SCHEMA_VERSION"]
