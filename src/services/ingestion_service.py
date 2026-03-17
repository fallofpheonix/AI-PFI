from __future__ import annotations

from pipeline.ingestion import IngestionRouter, RawFOA


class FOAIngestionService:
    def __init__(self, router: IngestionRouter | None = None):
        self._router = router or IngestionRouter()

    def fetch_raw_foa(self, source_url: str) -> RawFOA:
        normalized = (source_url or "").strip()
        if not normalized:
            raise ValueError("source_url cannot be empty")
        return self._router.ingest(normalized)
