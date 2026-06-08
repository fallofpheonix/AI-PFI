"""
NIH (National Institutes of Health) FOA Ingester.
Uses the NIH Reporter API and Research Portfolio Online Reporting Tools.
Also handles grants.nih.gov FOA pages.
"""

import re
import logging
from typing import Optional

from .base import BaseProvider, RawFOA

logger = logging.getLogger(__name__)

NIH_REPORTER_API = "https://api.reporter.nih.gov/v2/projects/search"
NIH_FOA_API = "https://grants.nih.gov/grants/guide/rfa-files"

import json

class NIHProvider(BaseProvider):
    """Ingest and parse FOAs from NIH."""

    def can_handle(self, url: str) -> bool:
        return any(d in url.lower() for d in ["nih.gov", "grants.nih.gov"])

    def fetch(self, url: str) -> RawFOA:
        if (
            url.lower().endswith(".html")
            or "rfa" in url.lower()
            or "pa-" in url.lower()
        ):
            return self._fetch_nih_guide_page(url)

        rfa_id = self._extract_rfa_id(url)
        if rfa_id:
            try:
                return self._fetch_via_api(url, rfa_id)
            except Exception as e:
                logger.warning(f"NIH API failed ({e}); falling back to HTML.")

        return self._fetch_via_html(url)

    def parse(self, raw_foa: RawFOA) -> dict:
        if raw_foa.raw_text and raw_foa.raw_text.strip().startswith("{"):
            try:
                data = json.loads(raw_foa.raw_text)
                return self._parse_json(data)
            except json.JSONDecodeError:
                pass

        return self._parse_text(raw_foa.raw_text or "", raw_foa.url)

    def _extract_rfa_id(self, url: str) -> Optional[str]:
        """Extract RFA/PA number from URL."""
        m = re.search(
            r"(?:RFA|PA|PAR|PAS|NOT)-(?:[A-Z]{2}-)?\d{2}-\d{3}", url, re.IGNORECASE
        )
        if m:
            return m.group(0)
        return None

    def _fetch_via_api(self, url: str, rfa_id: str) -> RawFOA:
        import requests

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
            url=url,
            agency="NIH",
            raw_text=raw_text,
            metadata={"rfa_id": rfa_id, "api_response": data},
        )

    def _fetch_nih_guide_page(self, url: str) -> RawFOA:
        from bs4 import BeautifulSoup

        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        raw_text = soup.get_text(separator="\n", strip=True)
        logger.info(f"NIH Guide page scraped: {url}")
        return RawFOA(
            url=url,
            agency="NIH",
            raw_html=resp.text,
            raw_text=raw_text,
        )

    def _fetch_via_html(self, url: str) -> RawFOA:
        return self._fetch_nih_guide_page(url)

    def _parse_json(self, data: dict) -> dict:
        result = {}
        projects = data.get("results", [{}])
        proj = projects[0] if projects else {}
        result["foa_id"] = proj.get("opportunity_number", "")
        result["title"] = proj.get("project_title", "")
        result["agency"] = proj.get("agency_ic_admin", {}).get("name", "NIH")
        result["open_date"] = self._parse_date(proj.get("project_start_date", ""))
        result["close_date"] = self._parse_date(proj.get("project_end_date", ""))
        result["description"] = proj.get("abstract_text", "")
        total = proj.get("award_amount")
        if total:
            result["award_range"] = {"max": int(total)}
        return result

    def _parse_text(self, text: str, url: str) -> dict:
        # Heuristics for NIH guide pages
        return {
            "foa_id": self._extract_rfa_id(url) or self._find_foa_id(text),
            "title": self._find_section(text, ["Funding Opportunity Title", "Department of Health and Human Services"]) or self._find_title(text),
            "agency": "National Institutes of Health",
            "open_date": self._find_date_near_keyword(text, ["Release Date"]),
            "close_date": self._find_date_near_keyword(text, ["Expiration Date"]),
            "source_url": url,
        }

