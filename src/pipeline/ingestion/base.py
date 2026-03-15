"""Shared ingestion primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RawFOA:
    """Raw FOA payload produced by ingestion modules."""

    source_url: str
    source_name: str
    raw_text: str = ""
    raw_html: str = ""
    raw_pdf_bytes: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseIngester:
    """Base class for source-specific ingesters."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AI-PFI/1.0; +https://github.com/fallofpheonix/AI-PFI)",
            "Accept": "*/*",
        }

    def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    def ingest(self, url: str) -> RawFOA:
        raise NotImplementedError

    def _get(self, url: str):
        import requests

        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response
