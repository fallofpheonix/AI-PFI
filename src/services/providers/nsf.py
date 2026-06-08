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

from .base import BaseProvider, RawFOA

logger = logging.getLogger(__name__)

NSF_API_BASE = "https://api.nsf.gov/services/v1"
NSF_PROGRAMS_API = f"{NSF_API_BASE}/awards.json"

import json

class NSFProvider(BaseProvider):
    """Ingest and parse FOAs from NSF."""

    def can_handle(self, url: str) -> bool:
        return "nsf.gov" in url.lower()

    def fetch(self, url: str) -> RawFOA:
        # PDF solicitation link?
        if url.lower().endswith(".pdf"):
            return self._fetch_pdf(url)

        # API call for program / award data?
        prog_id = self._extract_program_id(url)
        if prog_id:
            try:
                return self._fetch_via_api(url, prog_id)
            except Exception as e:
                logger.warning(f"NSF API failed ({e}); falling back to HTML.")

        return self._fetch_via_html(url)

    def parse(self, raw_foa: RawFOA) -> dict:
        if raw_foa.raw_text and raw_foa.raw_text.strip().startswith("{"):
            try:
                data = json.loads(raw_foa.raw_text)
                return self._parse_json(data)
            except json.JSONDecodeError:
                pass

        if raw_foa.raw_pdf_bytes:
            from core.extraction.pdf_extractor import extract_text_from_pdf
            text = extract_text_from_pdf(raw_foa.raw_pdf_bytes)
            return self._parse_text(text, raw_foa.url)

        return self._parse_text(raw_foa.raw_text or "", raw_foa.url)

    def _extract_program_id(self, url: str) -> Optional[str]:
        """Extract NSF program number (e.g. 23-615) from URL."""
        m = re.search(r"nsf(\d{2}-\d{3,4})", url, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"pims_id=(\d+)", url, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def _fetch_via_api(self, url: str, prog_id: str) -> RawFOA:
        import requests

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
            url=url,
            agency="NSF",
            raw_text=raw_text,
            metadata={"program_id": prog_id, "api_response": data},
        )

    def _fetch_via_html(self, url: str) -> RawFOA:
        from bs4 import BeautifulSoup

        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n", strip=True)
        logger.info(f"NSF HTML scrape: fetched {url}")
        return RawFOA(
            url=url,
            agency="NSF",
            raw_html=resp.text,
            raw_text=raw_text,
        )

    def _fetch_pdf(self, url: str) -> RawFOA:
        resp = self._get(url)
        logger.info(f"NSF PDF ingested: {url}")
        return RawFOA(
            url=url,
            agency="NSF",
            raw_pdf_bytes=resp.content,
        )

    def _parse_json(self, data: dict) -> dict:
        result = {}
        awards = data.get("response", {}).get("award", [{}])
        aw = awards[0] if awards else {}
        result["foa_id"] = aw.get("id", "")
        result["title"] = aw.get("title", "")
        result["agency"] = "National Science Foundation"
        result["open_date"] = self._parse_date(aw.get("startDate", ""))
        result["close_date"] = self._parse_date(aw.get("expDate", ""))
        result["description"] = aw.get("abstractText", "")
        funds = aw.get("fundsObligatedAmt")
        if funds:
            result["award_range"] = {"max": int(funds)}
        return result

    def _parse_text(self, text: str, url: str) -> dict:
        return {
            "foa_id": self._extract_program_id(url) or self._find_foa_id(text),
            "title": self._find_section(text, ["Funding Opportunity Title"]) or self._find_title(text),
            "agency": "National Science Foundation",
            "open_date": self._find_date_near_keyword(text, ["Posted Date"]),
            "close_date": self._find_date_near_keyword(text, ["Deadline"]),
            "source_url": url,
        }

