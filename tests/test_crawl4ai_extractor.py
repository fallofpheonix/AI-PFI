import pytest
from unittest.mock import AsyncMock, patch
from pipeline.extraction.crawl4ai_extractor import Crawl4AIExtractor

@pytest.mark.asyncio
async def test_crawl4ai_extractor_success():
    # Mocking the AsyncWebCrawler
    with patch("pipeline.extraction.crawl4ai_extractor.AsyncWebCrawler", autospec=True) as MockCrawler:
        mock_crawler_instance = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        
        # Mocking arun result
        mock_result = AsyncMock()
        mock_result.success = True
        mock_result.extracted_content = '[{"title": "Grant Title", "opportunity_number": "123"}]'
        mock_crawler_instance.arun.return_value = mock_result
        
        extractor = Crawl4AIExtractor()
        data = await extractor.extract_foa("https://example.com/foa")
        
        assert data["title"] == "Grant Title"
        assert data["opportunity_number"] == "123"
        mock_crawler_instance.arun.assert_called_once()

@pytest.mark.asyncio
async def test_crawl4ai_extractor_fallback():
    # Mocking the AsyncWebCrawler
    with patch("pipeline.extraction.crawl4ai_extractor.AsyncWebCrawler", autospec=True) as MockCrawler:
        mock_crawler_instance = AsyncMock()
        MockCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        
        # Mocking arun result with empty json
        mock_result = AsyncMock()
        mock_result.success = True
        mock_result.extracted_content = '[]'
        mock_result.markdown = '# Markdown Content'
        mock_crawler_instance.arun.return_value = mock_result
        
        extractor = Crawl4AIExtractor()
        data = await extractor.extract_foa("https://example.com/foa")
        
        assert data["raw_text_content"] == "# Markdown Content"
        assert data["fallback_triggered"] is True
