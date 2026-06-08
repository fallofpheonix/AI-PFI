from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AgencyEnum(str, Enum):
    GRANTS_GOV = "GRANTS_GOV"
    NIH = "NIH"
    NSF = "NSF"


class RawFOA(BaseModel):
    foa_id: Optional[str] = None
    title: Optional[str] = None
    agency: Optional[str] = None
    deadline_raw: Optional[str] = None
    url: str
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None
    raw_pdf_bytes: Optional[bytes] = None
    metadata: dict = Field(default_factory=dict)


class FOARecord(RawFOA):
    deadline: Optional[date] = None
    tags: List[str] = Field(default_factory=list)
    source: AgencyEnum
    # Fields from previous implementation that are required for functionality
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    eligibility: Optional[str] = None
    description: Optional[str] = None
    award_range: dict = Field(default_factory=dict)
    ingested_at: Optional[str] = None
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_csv_row(self) -> dict:
        payload = self.to_dict()
        # Flatten award range
        award_range = payload.get("award_range") or {}
        payload["award_min"] = award_range.get("min", "")
        payload["award_max"] = award_range.get("max", "")
        if "award_range" in payload:
            del payload["award_range"]
        
        # Flatten tags
        payload["tags_list"] = "|".join(payload.get("tags", []))
        if "tags" in payload:
            del payload["tags"]
        
        return payload

    @classmethod
    def csv_fieldnames(cls) -> list[str]:
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
            "url",
            "source",
            "ingested_at",
            "schema_version",
            "tags_list",
        ]


class ResearcherCreate(BaseModel):
    name: str
    email: str
    query: str
    match_threshold: float = 0.35


class ResearcherProfile(ResearcherCreate):
    id: int
