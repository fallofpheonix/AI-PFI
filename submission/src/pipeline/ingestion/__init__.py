"""FOA ingestion router and source adapters."""

from __future__ import annotations

from .base import BaseIngester, RawFOA
from .grants_gov import GrantsGovIngester
from .nsf import NSFIngester
from .nih import NIHIngester


class IngestionRouter:
    """Selects the first ingester that can process a URL."""

    def __init__(self):
        self.ingesters = [
            GrantsGovIngester(),
            NSFIngester(),
            NIHIngester(),
        ]

    def ingest(self, url: str) -> RawFOA:
        for ingester in self.ingesters:
            if ingester.can_handle(url):
                return ingester.ingest(url)
        raise ValueError(f"No ingester available for URL: {url}")


__all__ = [
    "BaseIngester",
    "RawFOA",
    "GrantsGovIngester",
    "NSFIngester",
    "NIHIngester",
    "IngestionRouter",
]
