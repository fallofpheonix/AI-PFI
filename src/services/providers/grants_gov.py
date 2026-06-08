"""
Grants.gov FOA Ingester.
Handles both the human-readable Grants.gov detail pages and
the public Grants.gov REST API (v1).
"""

import re
import logging
from typing import Optional

from .base import BaseProvider, RawFOA

logger = logging.getLogger(__name__)

GRANTS_GOV_API = "https://api.grants.gov/v1/api/fetchOpportunity"
GRANTS_GOV_SEARCH = "https://api.grants.gov/v1/api/search"


import json

class GrantsGovProvider(BaseProvider):
    """Ingest and parse FOAs from Grants.gov."""

    def can_handle(self, url: str) -> bool:
        return "grants.gov" in url.lower()

    def fetch(self, url: str) -> RawFOA:
        opp_id = self._extract_opportunity_id(url)

        # ── Try API first ──────────────────────────────────────────────────────
        if opp_id:
            try:
                return self._fetch_via_api(url, opp_id)
            except Exception as e:
                logger.warning(f"API fetch failed ({e}); falling back to HTML scrape.")

        # ── Fallback: scrape HTML ──────────────────────────────────────────────
        return self._fetch_via_html(url)

    def parse(self, raw_foa: RawFOA) -> dict:
        # If we have a JSON API response, extract from that
        if raw_foa.raw_text and raw_foa.raw_text.strip().startswith("{"):
            try:
                data = json.loads(raw_foa.raw_text)
                return self._parse_json(data)
            except json.JSONDecodeError:
                pass

        return self._parse_text(raw_foa.raw_text or "", raw_foa.url)

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

    def _fetch_via_api(self, url: str, opp_id: str) -> RawFOA:
        """Use the Grants.gov REST API to pull structured data."""
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

        # Serialize the JSON payload as raw_text so the extractor can parse it
        raw_text = json.dumps(data, indent=2)
        logger.info(f"Grants.gov API: fetched opportunity {opp_id}")
        return RawFOA(
            url=url,
            agency="Grants.gov",
            raw_text=raw_text,
            metadata={"opportunity_id": opp_id, "api_response": data},
        )

    def _fetch_via_html(self, url: str) -> RawFOA:
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
            url=url,
            agency="Grants.gov",
            raw_html=resp.text,
            raw_text=raw_text,
        )

    def _parse_json(self, data: dict) -> dict:
        result = {}
        root = data.get("data", data)
        synopsis = root.get("synopsis", {}) if isinstance(root, dict) else {}
        opp = data.get("opportunity", data.get("opportunityDetail", root))

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

    def _parse_text(self, text: str, url: str) -> dict:
        # Simplified text parsing for Grants.gov fallback
        return {
            "foa_id": self._extract_opportunity_id(url) or self._find_foa_id(text),
            "title": self._find_section(text, ["Opportunity Title"]) or self._find_title(text),
            "agency": self._find_section(text, ["Agency Name"]) or self._find_agency(text),
            "open_date": self._find_date_near_keyword(text, ["Posted Date"]),
            "close_date": self._find_date_near_keyword(text, ["Closing Date"]),
            "source_url": url,
        }

