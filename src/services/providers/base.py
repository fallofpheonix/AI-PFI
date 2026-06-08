"""Shared ingestion primitives."""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Optional
from core.models import RawFOA, FOARecord

logger = logging.getLogger(__name__)

_DATE_PATTERNS = [
    # ISO: 2024-03-15
    (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
    # US long: March 15, 2024  /  Mar 15, 2024
    (r"([A-Za-z]+ \d{1,2},?\s*\d{4})", "%B %d, %Y"),
    (r"([A-Za-z]{3}\.? \d{1,2},?\s*\d{4})", "%b %d, %Y"),
    # US short: 03/15/2024  or  03-15-2024
    (r"(\d{2}/\d{2}/\d{4})", "%m/%d/%Y"),
    (r"(\d{2}-\d{2}-\d{4})", "%m-%d-%Y"),
]


class BaseProvider:
    """Base class for source-specific providers handling ingestion and parsing."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AI-PFI/1.0; +https://github.com/fallofpheonix/AI-PFI)",
            "Accept": "*/*",
        }

    def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    def fetch(self, url: str) -> RawFOA:
        raise NotImplementedError

    def parse(self, raw_foa: RawFOA) -> dict:
        """
        Extract raw fields from RawFOA.
        Returns a dictionary of raw fields to be normalized.
        """
        raise NotImplementedError

    # ── Shared Helpers ────────────────────────────────────────────────────────

    def _get(self, url: str):
        import requests

        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response

    def _parse_date(self, raw: str) -> Optional[str]:
        """Return an ISO-8601 date string, or None if unparseable."""
        if not raw:
            return None
        raw = str(raw).strip().rstrip(",;")
        for pat, fmt in _DATE_PATTERNS:
            m = re.search(pat, raw)
            if m:
                try:
                    cleaned = m.group(1).strip()
                    try:
                        d = datetime.strptime(cleaned, fmt)
                    except ValueError:
                        d = datetime.strptime(
                            cleaned.replace(",", "").replace("  ", " ").strip(),
                            fmt.replace(", ", " "),
                        )
                    return d.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    def _safe_amount(self, value):
        """Parse integer-like funding values; return None for blank/non-numeric."""
        if value is None:
            return None
        s = str(value).strip()
        if not s or s.lower() in {"none", "n/a", "na", "null"}:
            return None
        try:
            return int(float(s.replace(",", "").replace("$", "")))
        except ValueError:
            return None

    def _extract_award_range(self, text: str) -> dict:
        """Extract min/max award amounts from free text."""
        amounts = []
        # $1,500,000 or $1.5M or $500K
        for m in re.finditer(r"\$\s*([\d,]+(?:\.\d+)?)\s*([MKBmkb])?", text):
            try:
                raw_num = float(m.group(1).replace(",", ""))
                suffix = (m.group(2) or "").upper()
                if suffix == "M":
                    raw_num *= 1_000_000
                elif suffix == "K":
                    raw_num *= 1_000
                elif suffix == "B":
                    raw_num *= 1_000_000_000
                amounts.append(int(raw_num))
            except ValueError:
                continue

        if not amounts:
            return {}
        amounts.sort()
        result = {"max": amounts[-1]}
        if len(amounts) > 1:
            result["min"] = amounts[0]
        return result

    def _find_date_near_keyword(self, text: str, keywords: list[str]) -> Optional[str]:
        """Find a date value appearing within ~120 chars of any keyword."""
        kw_pattern = "|".join(re.escape(k) for k in keywords)
        for m in re.finditer(kw_pattern, text, re.IGNORECASE):
            window = text[m.start() : m.start() + 120]
            for pat, fmt in _DATE_PATTERNS:
                dm = re.search(pat, window)
                if dm:
                    result = self._parse_date(dm.group(1))
                    if result:
                        return result
        return None

    def _find_section(self, text: str, keywords: list[str]) -> str:
        """Extract a paragraph that starts near any of the keywords."""
        for kw in keywords:
            m = re.search(
                rf"{re.escape(kw)}\s*[:\n](.+?)(?:\n\n|\Z)",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                content = m.group(1).strip()
                return content[:2000]
        return ""

    def _find_foa_id(self, text: str) -> str:
        """Try to find a funding opportunity identifier."""
        patterns = [
            r"(?:PA|RFA|PAR|PAS|NOT)-(?:[A-Z]{2}-)?\d{2}-\d{3}",  # NIH styles
            r"Opportunity\s+Number[:\s]+([A-Z0-9\-]+)",
            r"FOA\s*[#:\s]+([A-Z0-9\-]+)",
            r"NSF[\s\-](\d{2}-\d{3,4})",
            r"Award\s+Number[:\s]+([A-Z0-9\-]+)",
            r"Program\s+Number[:\s]+([A-Z0-9\-]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1) if m.lastindex else m.group(0)
        return ""

    def _find_title(self, text: str) -> str:
        """Heuristics to find the FOA title."""
        lines = text.split("\n")
        # Look for a line after "Title:" label
        for i, line in enumerate(lines):
            if re.match(r"(funding\s+)?title\s*:", line, re.IGNORECASE):
                candidate = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if candidate:
                    return candidate
            if re.match(r"title\s*:", line, re.IGNORECASE):
                after = re.sub(r"^title\s*:\s*", "", line, flags=re.IGNORECASE).strip()
                if after:
                    return after

        # Fallback: find lines that look like a title (title-case, ≥5 words)
        for line in lines[:40]:
            stripped = line.strip()
            if 5 <= len(stripped.split()) <= 20 and stripped[0].isupper():
                return stripped

        return ""

    def _find_agency(self, text: str) -> str:
        """Detect funding agency from text."""
        known_agencies = [
            ("National Science Foundation", "NSF"),
            ("National Institutes of Health", "NIH"),
            ("Department of Energy", "DOE"),
            ("Department of Defense", "DOD"),
            ("National Aeronautics and Space Administration", "NASA"),
            ("Environmental Protection Agency", "EPA"),
            ("Department of Agriculture", "USDA"),
            ("Department of Health and Human Services", "HHS"),
            ("National Endowment for the Humanities", "NEH"),
        ]
        for full, abbr in known_agencies:
            if full.lower() in text.lower() or abbr in text:
                return full

        # Label-based
        m = re.search(r"(?:agency|sponsor|funder)\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]

        return ""
