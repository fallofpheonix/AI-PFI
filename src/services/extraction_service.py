from __future__ import annotations

from core.models import RawFOA
from services.providers import ProviderRouter


class FOAExtractionService:
    def __init__(self, router: ProviderRouter | None = None):
        self._router = router or ProviderRouter()

    def extract_fields(self, raw_foa: RawFOA) -> dict:
        provider = self._router.get_provider(raw_foa.url)
        return provider.parse(raw_foa)
