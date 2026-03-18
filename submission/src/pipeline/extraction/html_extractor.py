"""
HTML / plain-text FOA field extractor.
Tries multiple heuristic strategies to pull structured fields from
raw HTML or clean text produced by the ingesters.
"""

import re
import json
import logging
from typing import Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)


# ── Date parsing helpers ───────────────────────────────────────────────────────

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


def _parse_date(raw: str) -> Optional[str]:
    """Return an ISO-8601 date string, or None if unparseable."""
    if not raw:
        return None
    raw = raw.strip().rstrip(",;")
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


def _find_date_near_keyword(text: str, keywords: list[str]) -> Optional[str]:
    """Find a date value appearing within ~120 chars of any keyword."""
    kw_pattern = "|".join(re.escape(k) for k in keywords)
    for m in re.finditer(kw_pattern, text, re.IGNORECASE):
        window = text[m.start() : m.start() + 120]
        for pat, fmt in _DATE_PATTERNS:
            dm = re.search(pat, window)
            if dm:
                result = _parse_date(dm.group(1))
                if result:
                    return result
    return None


# ── Award range helper ─────────────────────────────────────────────────────────


def _extract_award_range(text: str) -> dict:
    """Extract min/max award amounts from free text."""
    amounts = []
    # $1,500,000 or $1.5M or $500K
    for m in re.finditer(r"\$\s*([\d,]+(?:\.\d+)?)\s*([MKBmkb])?", text):
        raw_num = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").upper()
        if suffix == "M":
            raw_num *= 1_000_000
        elif suffix == "K":
            raw_num *= 1_000
        elif suffix == "B":
            raw_num *= 1_000_000_000
        amounts.append(int(raw_num))

    if not amounts:
        return {}
    amounts.sort()
    result = {"max": amounts[-1]}
    if len(amounts) > 1:
        result["min"] = amounts[0]
    return result


def _join_applicant_types(value) -> str:
    """Normalize Grants.gov applicantTypes payloads to a string."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                desc = item.get("description")
                if desc:
                    parts.append(str(desc))
            elif item:
                parts.append(str(item))
        return "; ".join(parts)
    return str(value)


def _safe_amount(value):
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


# ── Main extractor class ───────────────────────────────────────────────────────


class HTMLExtractor:
    """
    Extracts structured FOA fields from raw HTML or plain text.
    Tries JSON-API response first (if raw_text looks like JSON),
    then falls back to regex heuristics over plain text.
    """

    def extract(self, raw_foa) -> dict:
        """
        :param raw_foa: RawFOA dataclass
        :return: dict with extracted fields (pre-normalization)
        """
        # If we have a JSON API response, extract from that
        if raw_foa.raw_text and raw_foa.raw_text.strip().startswith("{"):
            try:
                data = json.loads(raw_foa.raw_text)
                result = self._extract_from_json(data, raw_foa.source_name)
                if result.get("title"):
                    result["source_url"] = raw_foa.source_url
                    return result
            except json.JSONDecodeError:
                pass

        # Otherwise use text heuristics
        text = raw_foa.raw_text or ""
        if raw_foa.raw_html and not text:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(raw_foa.raw_html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)

        return self._extract_from_text(text, raw_foa)

    # ── JSON extraction ────────────────────────────────────────────────────────

    def _extract_from_json(self, data: dict, source: str) -> dict:
        """Extract fields from a parsed API JSON response."""
        result = {}

        if source == "grants.gov":
            # Supports legacy opportunity/details payloads and fetchOpportunity payloads.
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
            result["open_date"] = _parse_date(
                str(
                    opp.get("openDate")
                    or opp.get("postDate")
                    or synopsis.get("postingDateStr")
                    or synopsis.get("postingDate", "")
                )
            )
            result["close_date"] = _parse_date(
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
                or _join_applicant_types(
                    synopsis.get("applicantTypes") or opp.get("applicantTypes")
                )
                or ""
            )
            result["description"] = (
                synopsis.get("synopsisDesc")
                or opp.get("description")
                or opp.get("synopsis", "")
            )

            award_min = _safe_amount(
                synopsis.get("awardFloor")
                or opp.get("awardFloor")
                or opp.get("awardMinimum")
            )
            award_max = _safe_amount(
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

        elif source == "nsf":
            awards = data.get("response", {}).get("award", [{}])
            aw = awards[0] if awards else {}
            result["foa_id"] = aw.get("id", "")
            result["title"] = aw.get("title", "")
            result["agency"] = "National Science Foundation"
            result["open_date"] = _parse_date(aw.get("startDate", ""))
            result["close_date"] = _parse_date(aw.get("expDate", ""))
            result["description"] = aw.get("abstractText", "")
            funds = aw.get("fundsObligatedAmt")
            if funds:
                result["award_range"] = {"max": int(funds)}

        elif source == "nih":
            projects = data.get("results", [{}])
            proj = projects[0] if projects else {}
            result["foa_id"] = proj.get("opportunity_number", "")
            result["title"] = proj.get("project_title", "")
            result["agency"] = proj.get("agency_ic_admin", {}).get("name", "NIH")
            result["open_date"] = _parse_date(proj.get("project_start_date", ""))
            result["close_date"] = _parse_date(proj.get("project_end_date", ""))
            result["description"] = proj.get("abstract_text", "")
            total = proj.get("award_amount")
            if total:
                result["award_range"] = {"max": int(total)}

        return result

    # ── Text heuristics extraction ─────────────────────────────────────────────

    def _extract_from_text(self, text: str, raw_foa) -> dict:
        lines = text.split("\n")
        result = {
            "foa_id": self._find_foa_id(text, raw_foa.source_name),
            "title": self._find_title(lines, text),
            "agency": self._find_agency(text, raw_foa.source_name),
            "open_date": _find_date_near_keyword(
                text, ["open date", "posted", "issue date", "published", "release date"]
            ),
            "close_date": _find_date_near_keyword(
                text,
                [
                    "close date",
                    "deadline",
                    "due date",
                    "application deadline",
                    "submission deadline",
                    "closing date",
                    "letter of intent",
                ],
            ),
            "eligibility": self._find_section(
                text, ["eligib", "who may apply", "applicant", "eligible organizations"]
            ),
            "description": self._find_section(
                text,
                [
                    "program description",
                    "overview",
                    "synopsis",
                    "summary",
                    "background",
                    "purpose",
                    "objectives",
                    "program goals",
                ],
            ),
            "award_range": _extract_award_range(text),
            "source_url": raw_foa.source_url,
        }
        return result

    def _find_foa_id(self, text: str, source: str) -> str:
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

    def _find_title(self, lines: list[str], text: str) -> str:
        """Heuristics to find the FOA title."""
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

    def _find_agency(self, text: str, source: str) -> str:
        """Detect funding agency from text or source name."""
        agency_map = {
            "grants.gov": "",  # agency is in data
            "nsf": "National Science Foundation",
            "nih": "National Institutes of Health",
        }
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

        return agency_map.get(source, source.upper())

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
                # Trim to ~2000 chars max
                return content[:2000]
        return ""
