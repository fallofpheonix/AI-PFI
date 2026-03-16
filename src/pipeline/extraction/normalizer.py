"""
FOA Normalizer.

Takes raw extracted fields and returns a fully validated,
schema-conformant FOARecord dataclass.
Schema version: 1.0
"""

import uuid
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"


@dataclass
class FOARecord:
    """
    Canonical FOA schema.

    All string fields default to "" (not None) for CSV-friendliness.
    Dates are ISO-8601 strings (YYYY-MM-DD) or "".
    award_range is a dict: {"min": int, "max": int} – keys optional.
    tags is populated by the tagging module.
    """

    # ── Core identifiers ──────────────────────────────────────────────────────
    foa_id: str = ""  # Funding opportunity number / generated UUID
    title: str = ""
    agency: str = ""

    # ── Dates ─────────────────────────────────────────────────────────────────
    open_date: str = ""  # ISO-8601
    close_date: str = ""  # ISO-8601

    # ── Narrative ─────────────────────────────────────────────────────────────
    eligibility: str = ""
    description: str = ""

    # ── Financials ────────────────────────────────────────────────────────────
    award_range: dict = field(default_factory=dict)  # {"min": int, "max": int}

    # ── Provenance ────────────────────────────────────────────────────────────
    source_url: str = ""
    source_name: str = ""  # "grants.gov" | "nsf" | "nih"
    ingested_at: str = ""  # ISO-8601 datetime

    # ── Tags (filled by tagging module) ───────────────────────────────────────
    tags: dict = field(default_factory=dict)

    # ── Schema metadata ───────────────────────────────────────────────────────
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)

    def to_csv_row(self) -> dict:
        """Flatten to a single-level dict suitable for csv.DictWriter."""
        d = self.to_dict()
        # Flatten award_range
        d["award_min"] = d["award_range"].get("min", "")
        d["award_max"] = d["award_range"].get("max", "")
        del d["award_range"]
        # Flatten tags
        for category, tag_list in d.get("tags", {}).items():
            d[f"tags_{category}"] = (
                "|".join(tag_list) if isinstance(tag_list, list) else str(tag_list)
            )
        del d["tags"]
        return d

    @classmethod
    def csv_fieldnames(cls) -> list:
        """Return ordered CSV column headers."""
        return [
            "foa_id",
            "title",
            "agency",
            "open_date",
            "close_date",
            "eligibility",
            "description",
            "award_min",
            "award_max",
            "source_url",
            "source_name",
            "ingested_at",
            "schema_version",
            "tags_research_domains",
            "tags_methods_approaches",
            "tags_populations",
            "tags_sponsor_themes",
        ]


class FOANormalizer:
    """Normalizes raw extracted fields into a validated FOARecord."""

    def normalize(self, extracted: dict, raw_foa=None) -> FOARecord:
        """
        :param extracted: dict from an extractor
        :param raw_foa: optional RawFOA for source metadata
        :return: FOARecord
        """
        rec = FOARecord()

        rec.foa_id = self._clean_id(extracted.get("foa_id", ""))
        rec.title = self._clean_str(extracted.get("title", ""), max_len=300)
        rec.agency = self._clean_str(extracted.get("agency", ""), max_len=200)
        rec.open_date = self._clean_date(extracted.get("open_date", ""))
        rec.close_date = self._clean_date(extracted.get("close_date", ""))
        rec.eligibility = self._clean_str(
            extracted.get("eligibility", ""), max_len=3000
        )
        rec.description = self._clean_str(
            extracted.get("description", ""), max_len=5000
        )
        rec.award_range = self._clean_award_range(extracted.get("award_range", {}))
        rec.source_url = extracted.get("source_url", "")
        rec.ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if raw_foa:
            rec.source_name = raw_foa.source_name

        # Generate a stable ID if none found
        if not rec.foa_id:
            seed = rec.source_url or rec.title or ""
            rec.foa_id = "FOA-" + str(uuid.uuid5(uuid.NAMESPACE_URL, seed))[:8].upper()
            logger.debug(f"Generated FOA ID: {rec.foa_id}")

        return rec

    # ── Field cleaners ────────────────────────────────────────────────────────

    def _clean_str(self, value, max_len: int = 5000) -> str:
        if not value:
            return ""
        s = str(value)
        # Collapse whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s[:max_len]

    def _clean_id(self, value) -> str:
        if not value:
            return ""
        s = str(value).strip()
        s = re.sub(r"\s+", "-", s)
        return s[:100]

    def _clean_date(self, value) -> str:
        if not value:
            return ""
        s = str(value).strip()
        # Already ISO-8601?
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s
        return ""

    def _clean_award_range(self, value) -> dict:
        if not isinstance(value, dict):
            return {}
        result = {}
        for key in ("min", "max"):
            v = value.get(key)
            if v is not None:
                try:
                    result[key] = int(float(str(v).replace(",", "")))
                except (ValueError, TypeError):
                    pass
        return result
