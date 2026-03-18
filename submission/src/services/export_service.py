from __future__ import annotations

from pathlib import Path

from pipeline.storage import FOAStore, export_batch_csv, export_batch_json, export_csv, export_json


class FOAExportService:
    def __init__(self, store_path: str | None = None):
        self._store = FOAStore(store_path) if store_path else None

    def maybe_upsert(self, record) -> bool:
        if not self._store:
            return False
        return self._store.upsert(record)

    def export_single(self, record, out_dir: str):
        json_path = export_json(record, out_dir)
        csv_path = export_csv(record, out_dir)
        return json_path, csv_path

    def export_batch(self, records: list, out_dir: str):
        if not records:
            return Path(out_dir) / "foa_batch.json", Path(out_dir) / "foa_batch.csv"
        return export_batch_json(records, out_dir), export_batch_csv(records, out_dir)
