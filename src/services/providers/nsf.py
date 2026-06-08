"""
NSF (National Science Foundation) FOA Provider.
Strictly uses the NSF Award Search API.
"""

import re
import logging
import json
from typing import Optional

from .base import BaseProvider, RawFOA

logger = logging.getLogger(__name__)

NSF_API_BASE = "https://api.nsf.gov/services/v1"
NSF_PROGRAMS_API = f"{NSF_API_BASE}/awards.json"


class NSFProvider(BaseProvider):
    """Ingest and parse FOAs from NSF via official API."""

    def can_handle(self, url: str) -> bool:
        return "nsf.gov" in url.lower()

    def fetch(self, url: str) -> RawFOA:
        prog_id = self._extract_program_id(url)
        if not prog_id:
            raise ValueError(f"Could not extract program identifier from NSF URL: {url}")

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
        
        if not data.get("response", {}).get("award"):
            raise ValueError(f"No results found in NSF API for program {prog_id}")

        raw_text = json.dumps(data, indent=2)
        logger.info(f"NSF API: fetched program {prog_id}")
        return RawFOA(
            url=url,
            agency="NSF",
            raw_text=raw_text,
            metadata={"program_id": prog_id, "api_response": data},
        )

    def parse(self, raw_foa: RawFOA) -> dict:
        if not raw_foa.raw_text:
            raise ValueError("Empty response from NSF API")
            
        try:
            data = json.loads(raw_foa.raw_text)
            return self._parse_json(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode NSF API response: {e}")

    def _extract_program_id(self, url: str) -> Optional[str]:
        """Extract NSF program number (e.g. 23-615) or pims_id from URL."""
        m = re.search(r"nsf(\d{2}-\d{3,4})", url, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"pims_id=(\d+)", url, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

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
            try:
                result["award_range"] = {"max": int(float(str(funds)))}
            except (ValueError, TypeError):
                pass
        return result
