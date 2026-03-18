"""
NSF (National Science Foundation) FOA Ingester.
Supports:
  - NSF Award Search API  (api.nsf.gov/services/v1/awards.json)
  - NSF Funding Opportunities HTML pages  (nsf.gov/funding/opportunities/*)
  - NSF Program Solicitations PDFs
"""

import re
import logging
from typing import Optional

from .base import BaseIngester, RawFOA

logger = logging.getLogger(__name__)

NSF_API_BASE = "https://api.nsf.gov/services/v1"
NSF_PROGRAMS_API = f"{NSF_API_BASE}/awards.json"


class NSFIngester(BaseIngester):
    """Ingest FOAs from NSF URLs."""

    def can_handle(self, url: str) -> bool:
        return "nsf.gov" in url.lower()

    def ingest(self, url: str) -> RawFOA:
        # PDF solicitation link?
        if url.lower().endswith(".pdf"):
            return self._ingest_pdf(url)

        # API call for program / award data?
        prog_id = self._extract_program_id(url)
        if prog_id:
            try:
                return self._ingest_via_api(url, prog_id)
            except Exception as e:
                logger.warning(f"NSF API failed ({e}); falling back to HTML.")

        return self._ingest_via_html(url)

    # ──────────────────────────────────────────────────────────────────────────

    def _extract_program_id(self, url: str) -> Optional[str]:
        """Extract NSF program number (e.g. 23-615) from URL."""
        m = re.search(r"nsf(\d{2}-\d{3,4})", url, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"pims_id=(\d+)", url, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def _ingest_via_api(self, url: str, prog_id: str) -> RawFOA:
        import requests, json

        params = {
            "programId": prog_id,
            "printFields": "id,title,agency,date,abstractText,fundProgramName,"
            "awardeeName,startDate,expDate,fundsObligatedAmt",
        }
        resp = requests.get(
            NSF_PROGRAMS_API,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = json.dumps(data, indent=2)
        logger.info(f"NSF API: fetched program {prog_id}")
        return RawFOA(
            source_url=url,
            source_name="nsf",
            raw_text=raw_text,
            metadata={"program_id": prog_id, "api_response": data},
        )

    def _ingest_via_html(self, url: str) -> RawFOA:
        from bs4 import BeautifulSoup

        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n", strip=True)
        logger.info(f"NSF HTML scrape: fetched {url}")
        return RawFOA(
            source_url=url,
            source_name="nsf",
            raw_html=resp.text,
            raw_text=raw_text,
        )

    def _ingest_pdf(self, url: str) -> RawFOA:
        resp = self._get(url)
        logger.info(f"NSF PDF ingested: {url}")
        return RawFOA(
            source_url=url,
            source_name="nsf",
            raw_pdf_bytes=resp.content,
        )
