import json
import logging
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

logger = logging.getLogger(__name__)

class Crawl4AIExtractor:
    """
    Adapts the Crawl4AI asynchronous crawling framework to match the 
    AI-PFI text extraction interface. Eliminates custom BeautifulSoup parsing.
    """
    
    def __init__(self):
        # Establish a flexible CSS-based map to catch common grant structure target patterns
        self.extraction_schema = {
            "name": "FundingOpportunityAnnouncement",
            "baseSelector": "body",
            "fields": [
                {"name": "title", "selector": "h1, .opportunity-title, #opportunity-title", "type": "text"},
                {"name": "opportunity_number", "selector": ".opp-num, [id*='opp-num'], .opportunity-number", "type": "text"},
                {"name": "posted_date", "selector": ".date-posted, [id*='posted'], .posted-date", "type": "text"},
                {"name": "close_date", "selector": ".date-close, [id*='close'], .close-date", "type": "text"},
                {"name": "description", "selector": ".opportunity-description, #description, .description-block", "type": "text"}
            ]
        }
        self.strategy = JsonCssExtractionStrategy(self.extraction_schema, verbose=False)

    async def extract_foa(self, url: str) -> Dict[str, Any]:
        """
        Asynchronously crawls the target URL, executes dynamic JavaScript, 
        and extracts structured metadata attributes based on our ontology map.
        """
        logger.info(f"Initiating Crawl4AI dynamic parse for target URL: {url}")
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=url,
                extraction_strategy=self.strategy,
                bypass_cache=True,
                # Explicitly wait for common async layout elements to populate
                wait_for="css:body" 
            )
            
            if not result.success:
                logger.error(f"Crawl4AI execution phase failed for {url}. Error: {result.error_message}")
                raise RuntimeError(f"Web ingestion failure: {result.error_message}")

            try:
                # Rehydrate string extraction results safely
                extracted_data = json.loads(result.extracted_content)
                
                if isinstance(extracted_data, list) and len(extracted_data) > 0:
                    data_block = extracted_data[0]
                elif isinstance(extracted_data, dict):
                    data_block = extracted_data
                else:
                    data_block = {}

                # If CSS schema comes up empty, fall back onto pristine layout markdown
                if not data_block or not data_block.get("title"):
                    logger.warning(f"CSS extraction returned sparse data for {url}. Falling back to raw markdown extraction.")
                    return {
                        "raw_text_content": result.markdown,
                        "fallback_triggered": True
                    }

                return data_block

            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to map structured extraction data stream: {e}")
                return {"raw_text_content": result.markdown, "fallback_triggered": True}
