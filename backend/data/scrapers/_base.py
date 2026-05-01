"""Shared HTTP base for Sprint 81 scrapers.

Conservative-by-default: sequential requests, 2s delay between calls, retry
with exponential backoff on 429 / 5xx, raises ``ScraperError`` on any failure
so the ingestion layer can fall back to the seed CSV.

Not a generic web scraper — only enough to hit Spotrac / ProSportsTransactions
/ Sports Reference once per night.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright as _sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _sync_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment,misc]
    _PLAYWRIGHT_AVAILABLE = False


class ScraperError(Exception):
    """Any failure inside a scraper — network, parse, anti-bot, etc.

    The ingestion service catches this and falls back to the seed CSV.
    """


# Rotate across a small pool of common desktop UAs. Single static UA invites
# rate-limit blocks; a small rotation looks like normal browsing without
# pretending to be a fleet of clients.
_USER_AGENT_POOL = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
)


class HttpScraper:
    """Rate-limited HTTP client. Subclass per source.

    Usage::

        class SpotracScraper(HttpScraper):
            BASE_URL = "https://www.spotrac.com"
            DELAY_SECONDS = 2.0

            def fetch_contracts(self, season):
                html = self.get(f"/nba/contracts/_/year/{season}")
                return self._parse(html)
    """

    BASE_URL: str = ""
    DELAY_SECONDS: float = 2.0
    TIMEOUT_SECONDS: float = 15.0
    MAX_RETRIES: int = 3

    def __init__(self) -> None:
        self.session = requests.Session()
        self._last_request_at: float = 0.0

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(_USER_AGENT_POOL),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _sleep_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.DELAY_SECONDS:
            time.sleep(self.DELAY_SECONDS - elapsed)
        self._last_request_at = time.monotonic()

    def get(self, path_or_url: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = path_or_url
        if not url.startswith("http"):
            url = self.BASE_URL.rstrip("/") + "/" + path_or_url.lstrip("/")

        backoff = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES):
            self._sleep_for_rate_limit()
            try:
                response = self.session.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "scraper request failed (attempt %d/%d) url=%s err=%s",
                    attempt + 1, self.MAX_RETRIES, url, exc,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code == 200:
                return response.text

            if response.status_code in (429, 503):
                logger.warning(
                    "scraper got %d (attempt %d/%d) url=%s — backing off %.1fs",
                    response.status_code, attempt + 1, self.MAX_RETRIES, url, backoff,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            # 4xx other than 429 — likely a permanent failure (anti-bot, dead link).
            raise ScraperError(
                "HTTP {0} from {1} — body[:200]={2}".format(
                    response.status_code, url, response.text[:200]
                )
            )

        raise ScraperError(
            "exhausted {0} retries for {1}: {2}".format(
                self.MAX_RETRIES, url, last_exc
            )
        )


class PlaywrightScraper:
    """Headless Chromium fetch for sites behind Cloudflare JS challenges.

    Uses playwright.sync_api (blocking — safe for cron, no asyncio required).
    Subclasses override scrape() exactly as with HttpScraper.

    One-time VM setup:
        venv/bin/pip install "playwright>=1.40.0"
        venv/bin/playwright install chromium --with-deps
    """

    BASE_URL: str = ""
    DELAY_SECONDS: float = 3.0
    BROWSER_TIMEOUT_MS: int = 30_000

    _USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    def __init__(self) -> None:
        if not _PLAYWRIGHT_AVAILABLE:
            raise ScraperError(
                "playwright package not installed. Run: "
                "pip install 'playwright>=1.40.0' && playwright install chromium --with-deps"
            )
        self._last_request_at: float = 0.0
        self._ua_index: int = 0

    def _sleep_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.DELAY_SECONDS:
            time.sleep(self.DELAY_SECONDS - elapsed)
        self._last_request_at = time.monotonic()

    def _next_user_agent(self) -> str:
        ua = self._USER_AGENTS[self._ua_index % len(self._USER_AGENTS)]
        self._ua_index += 1
        return ua

    def get(self, path_or_url: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = path_or_url
        if not url.startswith("http"):
            url = self.BASE_URL.rstrip("/") + "/" + path_or_url.lstrip("/")
        if params:
            from urllib.parse import urlencode
            sep = "&" if "?" in url else "?"
            url = url + sep + urlencode(params)

        self._sleep_for_rate_limit()

        browser = None
        try:
            with _sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent=self._next_user_agent(),
                    viewport={"width": 1280, "height": 800},
                )
                page.goto(url, timeout=self.BROWSER_TIMEOUT_MS, wait_until="networkidle")
                content = page.content()
                browser.close()
                browser = None
                return content
        except PlaywrightTimeoutError as exc:
            if browser is not None:
                browser.close()
            raise ScraperError(
                "Playwright timeout ({0}ms) fetching {1}: {2}".format(
                    self.BROWSER_TIMEOUT_MS, url, exc
                )
            )
        except Exception as exc:  # noqa: BLE001
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            raise ScraperError(
                "Playwright fetch failed for {0}: {1}".format(url, exc)
            )

    def scrape(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
