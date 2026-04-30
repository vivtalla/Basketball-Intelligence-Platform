"""Sprint 81 scraper modules — replace seed-CSV stubs with live data sources.

Each scraper exposes a single ``fetch_*()`` function that returns a list of
normalized dicts matching the corresponding seed-CSV schema. Callers wrap the
fetch in ``salary_ingestion_service`` / ``sync_injury_history`` /
``sync_draft_prospects`` and fall back to the seed CSV on ``ScraperError``.

Scrapers must:
- rate-limit themselves via the shared ``HttpScraper`` base
- raise ``ScraperError`` on any failure (network, parse, anti-bot) so the
  ingestion layer can fall back cleanly
- be deterministic against an HTML fixture (used in tests)
"""
from __future__ import annotations

from data.scrapers._base import HttpScraper, ScraperError

__all__ = ["HttpScraper", "ScraperError"]
