from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from core.models import FOARecord

logger = logging.getLogger(__name__)


class FOANormalizer:
    def normalize(self, extracted: dict, raw_foa=None) -> FOARecord:
        record = FOARecord()

        record.foa_id = self._normalize_identifier(extracted.get("foa_id", ""))
        record.title = self._normalize_text(extracted.get("title", ""), max_len=300)
        record.agency = self._normalize_text(extracted.get("agency", ""), max_len=200)
        record.open_date = self._normalize_iso_date(extracted.get("open_date", ""))
        record.close_date = self._normalize_iso_date(extracted.get("close_date", ""))
        record.eligibility = self._normalize_text(extracted.get("eligibility", ""), max_len=3000)
        record.description = self._normalize_text(extracted.get("description", ""), max_len=5000)
        record.award_range = self._normalize_award_range(extracted.get("award_range", {}))
        record.source_url = extracted.get("source_url", "")
        record.ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if raw_foa:
            record.source_name = getattr(raw_foa, "source_name", "")

        if not record.foa_id:
            seed = record.source_url or record.title or "untitled"
            record.foa_id = f"FOA-{str(uuid.uuid5(uuid.NAMESPACE_URL, seed))[:8].upper()}"
            logger.debug("Generated fallback FOA identifier: %s", record.foa_id)

        return record

    def _normalize_text(self, value, *, max_len: int) -> str:
        if not value:
            return ""
        normalized = re.sub(r"\s+", " ", str(value)).strip()
        return normalized[:max_len]

    def _normalize_identifier(self, value) -> str:
        if not value:
            return ""
        compact = re.sub(r"\s+", "-", str(value).strip())
        return compact[:100]

    def _normalize_iso_date(self, value) -> str:
        if not value:
            return ""
        date_value = str(value).strip()
        return date_value if re.match(r"^\d{4}-\d{2}-\d{2}$", date_value) else ""

    def _normalize_award_range(self, value) -> dict:
        if not isinstance(value, dict):
            return {}

        out = {}
        for field in ("min", "max"):
            numeric = value.get(field)
            if numeric is None:
                continue
            try:
                out[field] = int(float(str(numeric).replace(",", "")))
            except (ValueError, TypeError):
                continue
        return out
