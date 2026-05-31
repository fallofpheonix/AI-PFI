"""Shared ingestion primitives."""

from __future__ import annotations

import time
import logging
import socket
import ipaddress
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SSRFViolationError(ValueError):
    """Raised when an ingestion request attempts to hit a restricted network space."""
    pass


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

    def _is_safe_url(self, url: str) -> bool:
        """
        Validates that the target URL does not resolve to private, loopback,
        or link-local infrastructure.
        """
        try:
            parsed_url = urlparse(url)
            host = parsed_url.hostname
            if not host:
                return False

            # Resolve all associated IP addresses for the target hostname
            # getaddrinfo handles dual-stack (IPv4/IPv6) resolution safely
            addr_info = socket.getaddrinfo(host, None)
            for family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)

                # Flag loopbacks (127.0.0.1), private subnets (RFC 1918), and link-local profiles
                if (ip_obj.is_loopback or
                    ip_obj.is_private or
                    ip_obj.is_link_local or
                    ip_obj.is_multicast or
                    ip_obj.is_unspecified):
                    return False
            
            return True
        except Exception as e:
            logger.error(f"SSRF validation lookup failed for host verification: {e}")
            return False

    def _get(
        self,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retries: int = 3,
        backoff_factor: float = 2.0
    ):
        """Executes an HTTP GET request with built-in SSRF and retry mitigations."""
        import requests

        # Pre-flight check: Halt immediately if the target endpoint is internal
        if not self._is_safe_url(url):
            raise SSRFViolationError(f"Security Restriction: Requested URL target maps to a blocked network footprint: {url}")

        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)

        for attempt in range(1, retries + 1):
            try:
                response = requests.get(url, headers=request_headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == retries:
                    logger.error(f"Final ingestion attempt failed for URL: {url}. Error: {e}")
                    raise e

                sleep_time = backoff_factor ** attempt
                logger.warning(
                    f"Ingestion transient failure (Attempt {attempt}/{retries}) for {url}: {e}. "
                    f"Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)

