"""
Grants.gov FOA Provider.
Strictly uses the official Grants.gov REST API (v1).
"""

import re
import logging
import json
from typing import Optional

from .base import BaseProvider, RawFOA

logger = logging.getLogger(__name__)

GRANTS_GOV_API = "https://api.grants.gov/v1/api/fetchOpportunity"


class GrantsGovProvider(BaseProvider):
    """Ingest and parse FOAs from Grants.gov via official API."""

    def can_handle(self, url: str) -> bool:
        return "grants.gov" in url.lower()

    def fetch(self, url: str) -> RawFOA:
        opp_id = self._extract_opportunity_id(url)
        if not opp_id:
            raise ValueError(f"Could not extract opportunity ID from Grants.gov URL: {url}")

        import requests

        payload = {"opportunityId": int(opp_id)}
        resp = requests.post(
            GRANTS_GOV_API,
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Serialize the JSON payload as raw_text so the parser can handle it
        raw_text = json.dumps(data, indent=2)
        logger.info(f"Grants.gov API: fetched opportunity {opp_id}")
        return RawFOA(
            url=url,
            agency="Grants.gov",
            raw_text=raw_text,
            metadata={"opportunity_id": opp_id, "api_response": data},
        )

    def parse(self, raw_foa: RawFOA) -> dict:
        if not raw_foa.raw_text:
            raise ValueError("Empty response from Grants.gov API")
            
        try:
            data = json.loads(raw_foa.raw_text)
            return self._parse_json(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode Grants.gov API response: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_opportunity_id(self, url: str) -> Optional[str]:
        """Extract numeric opportunity ID from a Grants.gov URL."""
        patterns = [
            r"oppId=(\d+)",
            r"opportunity/(\d+)",
            r"synopsisId=(\d+)",
            r"/(\d{5,})",
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return None

    def _parse_json(self, data: dict) -> dict:
        result = {}
        # The API can return data wrapped in a "data" key or at the root
        root = data.get("data", data)
        if not isinstance(root, dict):
            root = data
            
        synopsis = root.get("synopsis", {})
        # Try finding opportunity in various places
        opp = root.get("opportunity") or root.get("opportunityDetail") or root
        if not isinstance(opp, dict):
            opp = root

        result["foa_id"] = str(
            synopsis.get("opportunityId")
            or opp.get("opportunityNumber")
            or synopsis.get("opportunityNumber")
            or opp.get("id", "")
        )
        result["title"] = (
            opp.get("opportunityTitle")
            or synopsis.get("opportunityTitle")
            or opp.get("title", "")
        )
        result["agency"] = (
            synopsis.get("agencyName")
            or opp.get("agencyName")
            or opp.get("agencyCode")
            or synopsis.get("agencyCode", "")
        )
        result["open_date"] = self._parse_date(
            str(
                opp.get("openDate")
                or opp.get("postDate")
                or synopsis.get("postingDateStr")
                or synopsis.get("postingDate", "")
            )
        )
        result["close_date"] = self._parse_date(
            str(
                opp.get("closeDate")
                or synopsis.get("responseDateStr")
                or synopsis.get("archiveDateStr")
                or opp.get("archiveDate")
                or synopsis.get("responseDate", "")
            )
        )
        result["eligibility"] = (
            synopsis.get("applicantEligibilityDesc")
            or opp.get("eligibilityDescription")
            or ""
        )
        result["description"] = (
            synopsis.get("synopsisDesc")
            or opp.get("description")
            or opp.get("synopsis", "")
        )

        award_min = self._safe_amount(
            synopsis.get("awardFloor")
            or opp.get("awardFloor")
            or opp.get("awardMinimum")
        )
        award_max = self._safe_amount(
            synopsis.get("awardCeiling")
            or opp.get("awardCeiling")
            or opp.get("awardMaximum")
        )
        if award_min is not None or award_max is not None:
            result["award_range"] = {}
            if award_min is not None:
                result["award_range"]["min"] = award_min
            if award_max is not None:
                result["award_range"]["max"] = award_max

        return result
