"""
D2C Scrapling Page Enricher — Stub/No-op implementation
=========================================================
Provides a no-op ScraplingPageEnricher for environments where
scrapling is not installed (e.g., GitHub Actions without ENABLE_DEEP_FETCH).

When scrapling IS installed, replace this with the real implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional


class ScraplingPageEnricher:
    """No-op page enricher. Returns empty enrichment data."""

    def __init__(self, enabled: bool = False, logger: Optional[logging.Logger] = None):
        self.enabled = enabled
        self.logger = logger or logging.getLogger(__name__)
        self._enrich_count = 0
        self._skip_count = 0

    @classmethod
    def from_env(
        cls,
        config: Any = None,
        logger: Optional[logging.Logger] = None,
    ) -> "ScraplingPageEnricher":
        """Construct from environment / config. Always returns disabled enricher."""
        return cls(enabled=False, logger=logger)

    def enrich(
        self,
        url: str,
        country: str = "us",
        fallback_title: str = "",
        fallback_snippet: str = "",
        **kwargs: Any,
    ) -> Dict[str, str]:
        """Return empty enrichment — caller falls back to Brave Search data."""
        self._skip_count += 1
        return {
            "page_title": "",
            "quote_original": "",
            "currency": "",
            "price_raw": "",
            "enriched": False,
        }

    def summary(self) -> str:
        return f"ScraplingEnricher(disabled): enriched={self._enrich_count}, skipped={self._skip_count}"
