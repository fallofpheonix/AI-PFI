"""
Storage / Export module.

Handles:
  - Single-record JSON / CSV export (for the screening task)
  - Batch export of multiple FOA records
  - Update workflow for incremental ingestion
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Union

from core.models import FOARecord

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
        # Use model_dump_json or model_dump for serializable output
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


# ── Update workflow ────────────────────────────────────────────────────────────


class FOAStore:
    """
    Persistent FOA store backed by a JSON-lines file.
    Supports incremental updates: skips already-ingested FOA IDs.
    """

    def __init__(self, store_path: Union[str, Path]):
        self.store_path = Path(store_path)
        self._records: dict = {}
        if self.store_path.exists():
            self._load()

    def _load(self):
        with open(self.store_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    self._records[rec["foa_id"]] = rec

    def contains(self, foa_id: str) -> bool:
        return foa_id in self._records

    def upsert(self, record: FOARecord) -> bool:
        """
        Insert or update by foa_id.
        Returns True only when store contents changed.
        """
        next_record = record.to_dict()
        # Ensure dict is serializable for comparison if needed, or just compare dicts
        prev_record = self._records.get(record.foa_id)
        if prev_record == next_record:
            return False

        self._records[record.foa_id] = next_record
        self._flush_snapshot()
        return True

    def _flush_snapshot(self):
        """Rewrite full JSONL snapshot to avoid duplicate records."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as fh:
            for foa_id in sorted(self._records.keys()):
                fh.write(
                    json.dumps(self._records[foa_id], ensure_ascii=False, default=str)
                    + "\n"
                )

    def all_records(self) -> List[dict]:
        return list(self._records.values())

    def export_snapshot(self, out_dir: Union[str, Path]):
        """Export current store as foa_batch.json + foa_batch.csv."""
        records = [FOARecord(**r) for r in self.all_records()]
        export_batch_json(records, out_dir)
        export_batch_csv(records, out_dir)
