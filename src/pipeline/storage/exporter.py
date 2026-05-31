import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Union, Optional

from core.models.foa_record import FOARecord

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
        json.dump(record.to_dict(), fh, indent=2, ensure_ascii=False)
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
    # Add any extra tag columns discovered at runtime
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
        json.dump([r.to_dict() for r in records], fh, indent=2, ensure_ascii=False)
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


# ── SQLite Database Storage ───────────────────────────────────────────────────


class FOAStore:
    """
    Thread-resilient transactional FOA storage engine backed by SQLite.
    Replaces the resource-intensive JSONL whole-file rewrite engine.
    """

    def __init__(self, database_path: Union[str, Path]):
        self.db_path = Path(database_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Generates database connections with optimized timeout tracking.
        """
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        # Row factory yields dictionary access structures effortlessly
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """
        Initializes the relational schema and activates Write-Ahead Logging (WAL).
        """
        with self._get_connection() as conn:
            # Optimize transaction concurrency using WAL mode journaling
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS foa_records (
                    foa_id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    title TEXT,
                    raw_payload TEXT NOT NULL, -- Stored as validated JSON string
                    extracted_at TEXT NOT NULL
                );
            """)
            conn.commit()

    def contains(self, foa_id: str) -> bool:
        """Determines if a given record uniquely exists in the dataset boundary."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM foa_records WHERE foa_id = ? LIMIT 1;", (foa_id,))
            return cursor.fetchone() is not None

    def upsert(self, record: FOARecord) -> bool:
        """
        Executes an atomic insert/update. Returns True if data is committed.
        """
        record_dict = record.to_dict()
        raw_payload = json.dumps(record_dict, ensure_ascii=False)

        with self._get_connection() as conn:
            # Pre-flight state comparison
            cursor = conn.execute(
                "SELECT raw_payload FROM foa_records WHERE foa_id = ?;", 
                (record.foa_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                if existing["raw_payload"] == raw_payload:
                    return False  # State unchanged
                
                # Update existing
                conn.execute("""
                    UPDATE foa_records 
                    SET source_name = ?, title = ?, raw_payload = ?, extracted_at = ?
                    WHERE foa_id = ?;
                """, (
                    record_dict.get("source_name"),
                    record_dict.get("title"),
                    raw_payload,
                    record_dict.get("ingested_at"),
                    record.foa_id
                ))
            else:
                # Insert new
                conn.execute("""
                    INSERT INTO foa_records (
                        foa_id, source_name, title, raw_payload, extracted_at
                    ) VALUES (?, ?, ?, ?, ?);
                """, (
                    record.foa_id,
                    record_dict.get("source_name"),
                    record_dict.get("title"),
                    raw_payload,
                    record_dict.get("ingested_at")
                ))
            conn.commit()
            return True

    def all_records(self) -> List[FOARecord]:
        """Collects all stored assets rehydrated into FOARecord objects."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT raw_payload FROM foa_records;")
            records = []
            for row in cursor.fetchall():
                data = json.loads(row["raw_payload"])
                records.append(_dict_to_record(data))
            return records

    def export_snapshot(self, out_dir: Union[str, Path]):
        """Export current store as foa_batch.json + foa_batch.csv."""
        records = self.all_records()
        export_batch_json(records, out_dir)
        export_batch_csv(records, out_dir)


def _dict_to_record(d: dict) -> FOARecord:
    r = FOARecord()
    for k, v in d.items():
        if hasattr(r, k):
            setattr(r, k, v)
    return r

