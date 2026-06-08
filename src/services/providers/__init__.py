"""FOA provider router and source adapters."""

from __future__ import annotations

from .base import BaseProvider, RawFOA
from .grants_gov import GrantsGovProvider
from .nsf import NSFProvider
from .nih import NIHProvider


class ProviderRouter:
    """Selects the first provider that can process a URL."""

    def __init__(self):
        self.providers = [
            GrantsGovProvider(),
            NSFProvider(),
            NIHProvider(),
        ]

    def get_provider(self, url: str) -> BaseProvider:
        for provider in self.providers:
            if provider.can_handle(url):
                return provider
        raise ValueError(f"No provider available for URL: {url}")


__all__ = [
    "BaseProvider",
    "RawFOA",
    "GrantsGovProvider",
    "NSFProvider",
    "NIHProvider",
    "ProviderRouter",
]
