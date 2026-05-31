from __future__ import annotations

import logging
from typing import Dict, Any
from pipeline.extraction.crawl4ai_extractor import Crawl4AIExtractor
from pipeline.extraction.pdf_extractor import MarkerExtractor

logger = logging.getLogger(__name__)

class FOAExtractionService:
    """
    Service facade wrapping extraction mechanisms.
    Provides native async interface for the pipeline.
    """
    
    def __init__(self):
        self.html_extractor = Crawl4AIExtractor()
        self.pdf_extractor = MarkerExtractor()

    async def extract_fields(self, raw_foa) -> Dict[str, Any]:
        """
        Asynchronous interface method for extraction.
        Routes based on content type.
        """
        if raw_foa.raw_pdf_bytes:
            return await self.pdf_extractor.extract_pdf(raw_foa.raw_pdf_bytes)
        
        return await self.html_extractor.extract_foa(raw_foa.source_url)


