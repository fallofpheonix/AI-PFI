"""
NIH (National Institutes of Health) FOA Provider.
Strictly uses the NIH Reporter API.
"""

import re
import logging
import json
from typing import Optional

from .base import BaseProvider, RawFOA

logger = logging.getLogger(__name__)

NIH_REPORTER_API = "https://api.reporter.nih.gov/v2/projects/search"


class NIHProvider(BaseProvider):
    """Ingest and parse FOAs from NIH via official API."""

    def can_handle(self, url: str) -> bool:
        return any(d in url.lower() for d in ["nih.gov", "grants.nih.gov"])

    def fetch(self, url: str) -> RawFOA:
        rfa_id = self._extract_rfa_id(url)
        if not rfa_id:
            raise ValueError(f"Could not extract RFA/PA identifier from NIH URL: {url}")

        import requests

        payload = {
            "criteria": {"foa": [rfa_id]},
            "limit": 1,
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
        
        if not data.get("results"):
            raise ValueError(f"No results found in NIH Reporter API for {rfa_id}")

        raw_text = json.dumps(data, indent=2)
        logger.info(f"NIH Reporter API: fetched {rfa_id}")
        return RawFOA(
            url=url,
            agency="NIH",
            raw_text=raw_text,
            metadata={"rfa_id": rfa_id, "api_response": data},
        )

    def parse(self, raw_foa: RawFOA) -> dict:
        if not raw_foa.raw_text:
            raise ValueError("Empty response from NIH API")
            
        try:
            data = json.loads(raw_foa.raw_text)
            return self._parse_json(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode NIH API response: {e}")

    def _extract_rfa_id(self, url: str) -> Optional[str]:
        """Extract RFA/PA number from URL."""
        m = re.search(
            r"(?:RFA|PA|PAR|PAS|NOT)-(?:[A-Z]{2}-)?\d{2}-\d{3}", url, re.IGNORECASE
        )
        if m:
            return m.group(0).upper()
        return None

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
