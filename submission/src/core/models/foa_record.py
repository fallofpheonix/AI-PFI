from __future__ import annotations

from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = "1.0"


@dataclass
class FOARecord:
    foa_id: str = ""
    title: str = ""
    agency: str = ""
    open_date: str = ""
    close_date: str = ""
    eligibility: str = ""
    description: str = ""
    award_range: dict = field(default_factory=dict)
    source_url: str = ""
    source_name: str = ""
    ingested_at: str = ""
    tags: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)

    def to_csv_row(self) -> dict:
        payload = self.to_dict()
        payload["award_min"] = payload["award_range"].get("min", "")
        payload["award_max"] = payload["award_range"].get("max", "")
        del payload["award_range"]

        for category, tags in payload.get("tags", {}).items():
            payload[f"tags_{category}"] = "|".join(tags) if isinstance(tags, list) else str(tags)
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
            "source_url",
            "source_name",
            "ingested_at",
            "schema_version",
            "tags_research_domains",
            "tags_methods_approaches",
            "tags_populations",
            "tags_sponsor_themes",
        ]
