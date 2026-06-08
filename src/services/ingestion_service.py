from __future__ import annotations

from services.providers import ProviderRouter, RawFOA


class FOAIngestionService:
    def __init__(self, router: ProviderRouter | None = None):
        self._router = router or ProviderRouter()

    def fetch_raw_foa(self, source_url: str) -> RawFOA:
        normalized = (source_url or "").strip()
        if not normalized:
            raise ValueError("source_url cannot be empty")
        
        provider = self._router.get_provider(normalized)
        return provider.fetch(normalized)
