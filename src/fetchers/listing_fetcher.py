#!/usr/bin/env python3
"""
Unified OLX Listing Details Fetcher (Async)
===========================================
Fetches full description, photos, and metadata from OLX listing pages
using a persistent, concurrent httpx client for high performance.

Provides:
- Async entrypoints: async with ListingDetailFetcher(): await fetch_listing_details(...) / fetch_batch_details(...)
- Convenience sync wrappers: fetch_listing_details_sync(...) and fetch_batch_details_sync(...) (use asyncio.run)
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio
from tqdm.contrib.logging import logging_redirect_tqdm

from src.core import config
from src.core.browser_transport import BrowserTransport
from src.fetchers.listing_parser import ListingParser
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# HTTP Status codes for unavailable pages
HTTP_NOT_FOUND = 404
HTTP_GONE = 410
HTTP_FORBIDDEN = 403


@dataclass
class BatchFetchStats:
    """Statistics for batch fetch operations."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    unavailable: int = 0
    skipped: int = 0

    def log_summary(self) -> None:
        """Log batch fetch statistics."""
        logger.info("=" * 80)
        logger.info("ASYNC BATCH FETCH COMPLETE")
        logger.info(f"Total processed: {self.total}")
        logger.info(
            f"  ✅ Successful: {self.successful} "
            f"(📦 Cached: {self.skipped}, 🌐 Newly fetched: {self.successful - self.skipped})"
        )
        if self.unavailable > 0:
            logger.info(f"  🗑️  Unavailable: {self.unavailable} (removed/expired/not found)")
        if self.failed > 0:
            logger.info(f"  ❌ Failed: {self.failed} (timeouts/errors)")
        logger.info("=" * 80)


class ListingDetailFetcher(ListingParser):
    """
    Async fetcher for OLX listing details using a persistent HTTP client.

    - Use as async with ListingDetailFetcher() to reuse HTTP connection pool.
    - Or use the provided sync wrappers if you need a synchronous callsite.
    """

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.client: httpx.AsyncClient | None = None
        logger.info("Async listing details fetcher initialized")

    # --- async context manager ------------------------------------------------
    async def __aenter__(self):
        """Initialize persistent HTTP client."""
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(config.REQUEST_TIMEOUT),
            follow_redirects=True,
            transport=BrowserTransport(),
        )
        logger.info("✅ Async HTTP client started (persistent connection pool)")
        return self

    async def __aexit__(self, *_args):
        """Cleanup HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.info("🔌 Async HTTP client closed")

    # --- page availability check (shared logic) ------------------------------
    def _check_page_availability(self, response: httpx.Response, url: str) -> dict | None:
        """Check if a page is unavailable (404, 410, 403)."""
        if response.status_code in [HTTP_NOT_FOUND, HTTP_GONE, HTTP_FORBIDDEN]:
            error_map = {
                HTTP_NOT_FOUND: ("Page not found (404)", "not_found"),
                HTTP_GONE: ("Listing removed or expired (410)", "removed"),
                HTTP_FORBIDDEN: ("Access forbidden (403)", "forbidden"),
            }
            error, error_type = error_map[response.status_code]
            logger.warning(f"❌ {error}: {url}")
            return {
                "description": "",
                "photos": [],
                "details": {},
                "fetched": False,
                "error": error,
                "error_type": error_type,
                "is_unavailable": True,
            }
        return None

    # --- async single listing fetch -----------------------------------------
    async def fetch_listing_details(self, url: str) -> dict:
        """Fetch full details from a single listing page asynchronously."""
        logger.debug(f"Fetching details from: {url}")

        if not self.client:
            raise RuntimeError("Client not initialized - use 'async with' context manager.")

        try:
            response = await self.client.get(url)

            if availability_error := self._check_page_availability(response, url):
                return availability_error

            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            description = self._extract_description(soup)
            photos = self._extract_photos(soup)
            details = self._extract_details(soup)
            metadata = self._extract_metadata(soup)

            logger.debug(
                f"✅ Extracted: {len(description)} chars, {len(photos)} photos, {metadata.get('views', 0)} views"
            )

            return {
                "description": description,
                "photos": photos,
                "details": details,
                "metadata": metadata,
                "fetched": True,
            }

        except httpx.TimeoutException:
            logger.error(f"⏱️  Timeout error for {url}")
            return {
                "description": "",
                "photos": [],
                "details": {},
                "fetched": False,
                "error": "Request timeout",
                "error_type": "timeout",
            }
        except httpx.ConnectError as e:
            logger.error(f"🔌 Connection error for {url}: {e}")
            return {
                "description": "",
                "photos": [],
                "details": {},
                "fetched": False,
                "error": f"Connection error: {e}",
                "error_type": "connection",
            }
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error for {url}: {e}")
            return {
                "description": "",
                "photos": [],
                "details": {},
                "fetched": False,
                "error": str(e),
                "error_type": "http",
            }
        except Exception as e:
            logger.error(f"⚠️  Parse error for {url}: {e}", exc_info=True)
            return {
                "description": "",
                "photos": [],
                "details": {},
                "fetched": False,
                "error": str(e),
                "error_type": "parse",
            }

    # --- helpers for caching & logging -------------------------------------
    def _is_cached(self, phone: dict, force_refetch: bool) -> bool:
        """Check if listing details are already cached"""
        return (
            not force_refetch
            and bool(phone.get("details_fetched"))
            and bool(phone.get("description"))
        )

    def _log_cached_listing(self, phone: dict, index: int, total: int) -> None:
        """Log information about cached listing"""
        desc_len = len(phone.get("description", ""))
        photo_count = len(phone.get("photos", []))
        views = phone.get("views", 0)
        title = phone.get("title", "Unknown")[:60]
        logger.info(f"[{index}/{total}] ⏭️  Already cached: {title}")
        logger.info(f"   {desc_len} chars, {photo_count} photos, {views} views")

    # --- create tasks & process results -----------------------------------
    def _create_fetch_tasks(
        self,
        listings: list[dict],
        max_listings: int,
        force_refetch: bool,
        stats: BatchFetchStats,
    ) -> list[Any]:
        """Create async tasks for fetching listing details"""
        tasks: list[Any] = []
        for i, phone in enumerate(listings[:max_listings], 1):
            url = phone.get("link")

            # Guard: Skip if no URL
            if not url:
                logger.warning(f"   ⚠️  No URL for listing: {phone.get('title')}")
                stats.failed += 1
                continue

            # Guard: Skip if already cached
            if self._is_cached(phone, force_refetch):
                self._log_cached_listing(phone, i, stats.total)
                stats.skipped += 1
                stats.successful += 1
                continue

            # Create async task for fetching
            logger.info(f"[{i}/{stats.total}] 🚀 Queuing: {phone.get('title', 'Unknown')[:60]}...")
            tasks.append(self.fetch_listing_details(url))

        return tasks

    def _process_batch_results(
        self,
        listings: list[dict],
        results: list[Any],
        max_listings: int,
        force_refetch: bool,
        stats: BatchFetchStats,
    ) -> None:
        """Process results from concurrent fetch operations"""
        task_index = 0

        for i, phone in enumerate(listings[:max_listings], 1):
            # Skip cached entries
            if self._is_cached(phone, force_refetch):
                continue

            if task_index >= len(results):
                break

            details = results[task_index]
            task_index += 1

            # Handle exceptions from gather
            if isinstance(details, Exception):
                logger.error(f"[{i}/{stats.total}] ❌ Exception: {details}")
                self._mark_as_failed(phone, str(details))
                stats.failed += 1
                continue

            # Handle fetch result
            result_type, count = self._handle_fetch_result(phone, details)
            if result_type == "success":
                stats.successful += count
            elif result_type == "unavailable":
                stats.unavailable += count
            else:
                stats.failed += count

    def _mark_as_failed(self, phone: dict, error: str) -> None:
        """Mark a phone listing as failed to fetch"""
        phone["description"] = ""
        phone["photos"] = []
        phone["details_fetched"] = False
        phone["fetch_error"] = error

    def _handle_fetch_result(self, phone: dict, details: dict) -> tuple[str, int]:
        """Handle fetch result and update phone data (same behavior as previous sync_fetch)"""
        if details.get("fetched"):
            phone["description"] = details["description"]
            phone["photos"] = details["photos"]
            phone["listing_details"] = details["details"]
            phone["metadata"] = details.get("metadata", {})
            phone["views"] = details.get("metadata", {}).get("views", 0)
            phone["details_fetched"] = True

            views = details.get("metadata", {}).get("views", 0)
            logger.info(
                f"   ✅ Got {len(details['description'])} chars, {len(details['photos'])} photos, {views} views"
            )
            return "success", 1

        # Handle unavailable pages (404, 410, 403)
        if details.get("is_unavailable"):
            phone["description"] = ""
            phone["photos"] = []
            phone["details_fetched"] = False
            phone["is_unavailable"] = True
            phone["unavailable_reason"] = details.get("error", "")
            phone["error_type"] = details.get("error_type", "unknown")

            error_type = details.get("error_type", "unknown")
            error_icons = {
                "not_found": "🔍",
                "removed": "🗑️",
                "forbidden": "⛔",
            }
            icon = error_icons.get(error_type, "❌")
            logger.warning(f"   {icon} Listing unavailable: {details.get('error')}")
            return "unavailable", 1

        # Other failures (timeout, connection, parse errors)
        phone["description"] = ""
        phone["photos"] = []
        phone["details_fetched"] = False
        phone["fetch_error"] = details.get("error", "Unknown error")
        phone["error_type"] = details.get("error_type", "unknown")

        logger.warning(f"   ❌ Failed to fetch: {details.get('error', 'Unknown error')}")
        return "failed", 1

    # --- public async batch method ----------------------------------------
    async def fetch_batch_details(
        self, listings: list[dict], max_listings: int = 50, force_refetch: bool = False
    ) -> list[dict]:
        """Fetch details for multiple listings concurrently."""
        stats = BatchFetchStats(total=min(len(listings), max_listings))

        logger.info("=" * 80)
        logger.info(f"ASYNC BATCH FETCH - TOP {stats.total} LISTINGS")
        logger.info("=" * 80)

        # Create fetch tasks (skips cached entries)
        tasks = self._create_fetch_tasks(listings, max_listings, force_refetch, stats)

        # Execute all fetches concurrently with progress bar
        if tasks:
            logger.info(f"⚡ Executing {len(tasks)} concurrent HTTP requests...")

            # Use asyncio.gather with tqdm wrapper for progress
            with logging_redirect_tqdm():
                # keep return_exceptions default (False) because we handle exceptions in _process_batch_results
                results = await tqdm_asyncio.gather(
                    *tasks,
                    desc="🌐 Fetching details (concurrent)",
                    unit="listing",
                    colour="blue",
                    leave=False,
                    position=0,
                    dynamic_ncols=True,
                )

            # Process results and update statistics
            self._process_batch_results(listings, results, max_listings, force_refetch, stats)
        else:
            logger.info("No URLs queued (all cached or none available).")

        # Log summary
        stats.log_summary()

        return listings

    # --- synchronous convenience wrappers ---------------------------------
    # These use asyncio.run to execute the async methods so existing sync callsites can keep working.
    def fetch_listing_details_sync(self, url: str) -> dict:
        """Sync wrapper for fetch_listing_details."""

        async def _run():
            async with ListingDetailFetcher() as fetcher:
                return await fetcher.fetch_listing_details(url)

        return asyncio.run(_run())

    def fetch_batch_details_sync(
        self, listings: list[dict], max_listings: int = 50, force_refetch: bool = False
    ) -> list[dict]:
        """Sync wrapper for fetch_batch_details."""

        async def _run():
            async with ListingDetailFetcher() as fetcher:
                return await fetcher.fetch_batch_details(
                    listings, max_listings=max_listings, force_refetch=force_refetch
                )

        return asyncio.run(_run())
