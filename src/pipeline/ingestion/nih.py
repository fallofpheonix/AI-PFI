"""
NIH (National Institutes of Health) FOA Ingester.
Uses the NIH Reporter API and Research Portfolio Online Reporting Tools.
Also handles grants.nih.gov FOA pages.
"""

import re
import logging
from typing import Optional

from .base import BaseIngester, RawFOA

logger = logging.getLogger(__name__)

NIH_REPORTER_API = "https://api.reporter.nih.gov/v2/projects/search"
NIH_FOA_API = "https://grants.nih.gov/grants/guide/rfa-files"


class NIHIngester(BaseIngester):
    """Ingest FOAs from NIH/grants.nih.gov URLs."""

    def can_handle(self, url: str) -> bool:
        return any(d in url.lower() for d in ["nih.gov", "grants.nih.gov"])

    def ingest(self, url: str) -> RawFOA:
        if (
            url.lower().endswith(".html")
            or "rfa" in url.lower()
            or "pa-" in url.lower()
        ):
            return self._ingest_nih_guide_page(url)

        rfa_id = self._extract_rfa_id(url)
        if rfa_id:
            try:
                return self._ingest_via_api(url, rfa_id)
            except Exception as e:
                logger.warning(f"NIH API failed ({e}); falling back to HTML.")

        return self._ingest_via_html(url)

    def _extract_rfa_id(self, url: str) -> Optional[str]:
        """Extract RFA/PA number from URL."""
        m = re.search(
            r"(?:RFA|PA|PAR|PAS|NOT)-(?:[A-Z]{2}-)?\d{2}-\d{3}", url, re.IGNORECASE
        )
        if m:
            return m.group(0)
        return None

    def _ingest_via_api(self, url: str, rfa_id: str) -> RawFOA:
        import requests, json

        payload = {
            "criteria": {"foa": [rfa_id]},
            "limit": 10,
            "offset": 0,
        }
        resp = requests.post(
            NIH_REPORTER_API,
            json=payload,
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = json.dumps(data, indent=2)
        logger.info(f"NIH Reporter API: fetched {rfa_id}")
        return RawFOA(
            source_url=url,
            source_name="nih",
            raw_text=raw_text,
            metadata={"rfa_id": rfa_id, "api_response": data},
        )

    def _ingest_nih_guide_page(self, url: str) -> RawFOA:
        from bs4 import BeautifulSoup

        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        raw_text = soup.get_text(separator="\n", strip=True)
        logger.info(f"NIH Guide page scraped: {url}")
        return RawFOA(
            source_url=url,
            source_name="nih",
            raw_html=resp.text,
            raw_text=raw_text,
        )

    def _ingest_via_html(self, url: str) -> RawFOA:
        return self._ingest_nih_guide_page(url)
