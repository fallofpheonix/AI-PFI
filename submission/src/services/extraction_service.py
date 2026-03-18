from __future__ import annotations

from pipeline.extraction import HTMLExtractor, extract_text_from_pdf


class FOAExtractionService:
    def __init__(self, extractor: HTMLExtractor | None = None):
        self._extractor = extractor or HTMLExtractor()

    def extract_fields(self, raw_foa) -> dict:
        if raw_foa.raw_pdf_bytes and not raw_foa.raw_text:
            raw_foa.raw_text = extract_text_from_pdf(raw_foa.raw_pdf_bytes)
        return self._extractor.extract(raw_foa)
