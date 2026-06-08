from __future__ import annotations

import json
from datetime import date
from typing import List, Optional

from sqlmodel import Field, SQLModel, Column, String


class FOAEntity(SQLModel, table=True):
    __tablename__ = "funding_opportunities"

    foa_id: str = Field(primary_key=True, index=True)
    title: Optional[str] = None
    agency: Optional[str] = None
    url: str
    source: str
    
    # Dates
    deadline: Optional[date] = None
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    
    # Text fields
    eligibility: Optional[str] = Field(default=None, sa_column=Column(String))
    description: Optional[str] = Field(default=None, sa_column=Column(String))
    
    # JSON-backed fields
    award_range_json: str = Field(default="{}", description="JSON string of award range min/max")
    tags_json: str = Field(default="[]", description="JSON string of tags list")
    
    ingested_at: Optional[str] = None
    schema_version: str = "1.0"

    @property
    def award_range(self) -> dict:
        return json.loads(self.award_range_json)

    @award_range.setter
    def award_range(self, value: dict):
        self.award_range_json = json.dumps(value)

    @property
    def tags(self) -> List[str]:
        return json.loads(self.tags_json)

    @tags.setter
    def tags(self, value: List[str]):
        self.tags_json = json.dumps(value)
