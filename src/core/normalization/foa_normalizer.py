from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from core.models import FOARecord, AgencyEnum, RawFOA

logger = logging.getLogger(__name__)


class FOANormalizer:
    def normalize(self, extracted: dict, raw_foa: RawFOA = None) -> FOARecord:
        # Map source name to AgencyEnum
        source = AgencyEnum.GRANTS_GOV
        if raw_foa:
            name = (raw_foa.agency or "").lower()
            if "nih" in name:
                source = AgencyEnum.NIH
            elif "nsf" in name:
                source = AgencyEnum.NSF

        record = FOARecord(
            url=raw_foa.url if raw_foa else extracted.get("source_url", ""),
            source=source,
            foa_id=self._normalize_identifier(extracted.get("foa_id", "")),
            title=self._normalize_text(extracted.get("title", ""), max_len=300),
            agency=self._normalize_text(extracted.get("agency", ""), max_len=200),
            open_date=self._normalize_iso_date(extracted.get("open_date", "")),
            close_date=self._normalize_iso_date(extracted.get("close_date", "")),
            eligibility=self._normalize_text(extracted.get("eligibility", ""), max_len=3000),
            description=self._normalize_text(extracted.get("description", ""), max_len=5000),
            award_range=self._normalize_award_range(extracted.get("award_range", {})),
            ingested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        if not record.foa_id:
            seed = record.url or record.title or "untitled"
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
