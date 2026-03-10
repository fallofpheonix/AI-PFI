"""
Grants.gov FOA Ingester.
Handles both the human-readable Grants.gov detail pages and
the public Grants.gov REST API (v1).
"""

import re
import logging
from typing import Optional

from .base import BaseIngester, RawFOA

logger = logging.getLogger(__name__)

GRANTS_GOV_API = "https://api.grants.gov/v1/api/opportunity/details"
GRANTS_GOV_SEARCH = "https://api.grants.gov/v1/api/search"


class GrantsGovIngester(BaseIngester):
    """Ingest FOAs from Grants.gov URLs or opportunity IDs."""

    def can_handle(self, url: str) -> bool:
        return "grants.gov" in url.lower()

    def ingest(self, url: str) -> RawFOA:
        import requests

        opp_id = self._extract_opportunity_id(url)

        # ── Try API first ──────────────────────────────────────────────────────
        if opp_id:
            try:
                return self._ingest_via_api(url, opp_id)
            except Exception as e:
                logger.warning(f"API fetch failed ({e}); falling back to HTML scrape.")

        # ── Fallback: scrape HTML ──────────────────────────────────────────────
        return self._ingest_via_html(url)

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_opportunity_id(self, url: str) -> Optional[str]:
        """Extract numeric opportunity ID from a Grants.gov URL."""
        patterns = [
            r"oppId=(\d+)",
            r"opportunity/(\d+)",
            r"synopsisId=(\d+)",
            r"/(\d{5,})",          # bare numeric segment ≥5 digits
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return None

    def _ingest_via_api(self, url: str, opp_id: str) -> RawFOA:
        """Use the Grants.gov REST API to pull structured data."""
        import requests, json

        params = {"oppId": opp_id}
        resp = requests.get(
            GRANTS_GOV_API,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Serialize the JSON payload as raw_text so the extractor can parse it
        raw_text = json.dumps(data, indent=2)
        logger.info(f"Grants.gov API: fetched opportunity {opp_id}")
        return RawFOA(
            source_url=url,
            source_name="grants.gov",
            raw_text=raw_text,
            metadata={"opportunity_id": opp_id, "api_response": data},
        )

    def _ingest_via_html(self, url: str) -> RawFOA:
        """Scrape the Grants.gov detail page HTML."""
        from bs4 import BeautifulSoup

        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav/footer noise
        for tag in soup(["nav", "footer", "script", "style"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n", strip=True)
        logger.info(f"Grants.gov HTML scrape: fetched {url}")
        return RawFOA(
            source_url=url,
            source_name="grants.gov",
            raw_html=resp.text,
            raw_text=raw_text,
        )
