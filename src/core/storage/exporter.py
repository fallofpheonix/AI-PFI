"""
Storage / Export module.

Handles:
  - Single-record JSON / CSV export (for the screening task)
  - Batch export of multiple FOA records
  - SQLite database persistence using SQLModel
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Union

from sqlmodel import Session, select

from core.models import FOARecord, AgencyEnum
from core.database.entities import FOAEntity
from core.database.session import engine, init_db

logger = logging.getLogger(__name__)


# ── Single-record helpers (screening task compatible) ─────────────────────────


def export_json(
    record: FOARecord, out_dir: Union[str, Path], filename: str = "foa.json"
) -> Path:
    """Write a single FOARecord to <out_dir>/<filename>."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record.to_dict(), fh, indent=2, ensure_ascii=False, default=str)
    logger.info(f"JSON exported → {out_path}")
    return out_path


def export_csv(
    record: FOARecord, out_dir: Union[str, Path], filename: str = "foa.csv"
) -> Path:
    """Write a single FOARecord to <out_dir>/<filename>."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    row = record.to_csv_row()
    fieldnames = FOARecord.csv_fieldnames()
    # Add any extra fields discovered at runtime
    for k in row:
        if k not in fieldnames:
            fieldnames.append(k)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerow(row)
    logger.info(f"CSV exported → {out_path}")
    return out_path


# ── Batch helpers ─────────────────────────────────────────────────────────────


def export_batch_json(
    records: List[FOARecord],
    out_dir: Union[str, Path],
    filename: str = "foa_batch.json",
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            [r.to_dict() for r in records], fh, indent=2, ensure_ascii=False, default=str
        )
    logger.info(f"Batch JSON exported ({len(records)} records) → {out_path}")
    return out_path


def export_batch_csv(
    records: List[FOARecord],
    out_dir: Union[str, Path],
    filename: str = "foa_batch.csv",
) -> Path:
    if not records:
        logger.warning("No records to export.")
        return Path(out_dir) / filename
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    rows = [r.to_csv_row() for r in records]
    fieldnames = FOARecord.csv_fieldnames()
    for row in rows:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Batch CSV exported ({len(records)} records) → {out_path}")
    return out_path


# ── Database Store ────────────────────────────────────────────────────────────


class FOAStore:
    """
    Persistent FOA store backed by SQLite (via SQLModel).
    Supports incremental updates: skips already-ingested FOA IDs.
    """

    def __init__(self, store_path: Union[str, Path] = None):
        # store_path is ignored now as we use DEFAULT_DB_PATH from session.py
        # but kept for signature compatibility
        init_db()

    def contains(self, foa_id: str) -> bool:
        with Session(engine) as session:
            statement = select(FOAEntity).where(FOAEntity.foa_id == foa_id)
            return session.exec(statement).first() is not None

    def upsert(self, record: FOARecord) -> bool:
        """
        Insert or update by foa_id.
        Returns True when record was updated or inserted.
        """
        with Session(engine) as session:
            existing = session.get(FOAEntity, record.foa_id)
            entity = self._record_to_entity(record)
            
            if existing:
                # Update existing fields
                for key, value in entity.model_dump(exclude={"foa_id"}).items():
                    setattr(existing, key, value)
                session.add(existing)
            else:
                session.add(entity)
            
            session.commit()
            return True

    def all_records(self) -> List[FOARecord]:
        with Session(engine) as session:
            statement = select(FOAEntity)
            entities = session.exec(statement).all()
            return [self._entity_to_record(e) for e in entities]

    def export_snapshot(self, out_dir: Union[str, Path]):
        """Export current store as foa_batch.json + foa_batch.csv."""
        records = self.all_records()
        export_batch_json(records, out_dir)
        export_batch_csv(records, out_dir)

    def _record_to_entity(self, record: FOARecord) -> FOAEntity:
        entity = FOAEntity(
            foa_id=record.foa_id,
            title=record.title,
            agency=record.agency,
            url=record.url,
            source=record.source.value,
            deadline=record.deadline,
            open_date=record.open_date,
            close_date=record.close_date,
            eligibility=record.eligibility,
            description=record.description,
            ingested_at=record.ingested_at,
            schema_version=record.schema_version,
        )
        entity.award_range = record.award_range
        entity.tags = record.tags
        return entity

    def _entity_to_record(self, entity: FOAEntity) -> FOARecord:
        return FOARecord(
            foa_id=entity.foa_id,
            title=entity.title,
            agency=entity.agency,
            url=entity.url,
            source=AgencyEnum(entity.source),
            deadline=entity.deadline,
            open_date=entity.open_date,
            close_date=entity.close_date,
            eligibility=entity.eligibility,
            description=entity.description,
            award_range=entity.award_range,
            tags=entity.tags,
            ingested_at=entity.ingested_at,
            schema_version=entity.schema_version,
        )
