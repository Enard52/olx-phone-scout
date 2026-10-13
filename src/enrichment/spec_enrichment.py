#!/usr/bin/env python3
"""
Phone Specification Enrichment
================================
Enrich phone listings with specs from Kimovil.com

Features:
- Async batch processing
- Cache-first approach (never re-scrape)
- Graceful degradation (if scraping fails, use description)
- Brand + model extraction from titles
"""

import asyncio
import re
from typing import Any

from src.core import constants
from src.detection.model_patterns import BRAND_ALIASES, MODEL_PATTERNS
from src.detection.patterns import strip_exchange_wish
from src.enrichment.kimovil_scraper import KimovilScraper
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SpecEnricher:
    """
    Enrich phone listings with specs from Kimovil.com using Playwright

    Features:
    - Real browser scraping (95-99% success rate)
    - Comprehensive spec extraction (30+ fields)
    - SQLite caching (permanent storage)
    - Rate limiting (respectful to server)
    """

    def __init__(self, cache_db: str | None = None):
        """
        Initialize spec enricher with Playwright scraper

        Args:
            cache_db: Path to cache database (uses global cache if None)

        Note:
            Cache is global and shared across ALL sessions.
            Phone specs don't change, so all sessions benefit from the same cache.
        """
        # Use global cache (shared across all sessions)
        # Pass None to use default global cache from KimovilScraper
        try:
            self.scraper: KimovilScraper | None = KimovilScraper(cache_db=cache_db)
            logger.info("✅ Kimovil Playwright scraper initialized (global cache)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize Playwright scraper: {e}")
            logger.warning("   Continuing without spec enrichment")
            self.scraper = None

    def extract_brand_and_model(self, title: str) -> tuple[str, str] | None:
        """
        Extract brand and model from phone title

        Args:
            title: Phone listing title

        Returns:
            (brand, model) tuple or None

        Examples:
            "Samsung S23 Ultra 256GB" → ("Samsung", "Galaxy S23 Ultra")
            "Xiaomi Redmi Note 12 Pro" → ("Xiaomi", "Redmi Note 12 Pro")

        Note:
            This uses a simplified extraction. For production, consider using
            brand_patterns.py for consistent brand detection across the codebase.
        """
        title_lower = title.lower()
        detected_brand = None
        for brand, keywords in BRAND_ALIASES.items():
            if any(kw in title_lower for kw in keywords):
                detected_brand = brand.title()
                break

        if not detected_brand:
            return None

        # Extract model using patterns
        if detected_brand.lower() in MODEL_PATTERNS:
            patterns = MODEL_PATTERNS[detected_brand.lower()]
            for pattern, formatter in patterns:
                match = re.search(pattern, title_lower)
                if match:
                    model = formatter(match)
                    return (detected_brand, model)

        return None

    async def enrich_phone(self, phone: dict[str, Any]) -> dict[str, Any]:
        """
        Enrich single phone with specs from Kimovil

        Args:
            phone: Phone dict with 'title' key

        Returns:
            Phone dict with added 'kimovil_specs' key
        """
        title = phone.get("title", "")

        # Extract brand and model
        extracted = self.extract_brand_and_model(strip_exchange_wish(title))
        if not extracted:
            phone["kimovil_specs"] = None
            return phone

        brand, model = extracted

        # Check if scraper is available
        if self.scraper is None:
            phone["kimovil_specs"] = None
            return phone

        # Fetch specs using Playwright (cache-first)
        specs = await self.scraper.scrape_phone_specs(brand, model)
        phone["kimovil_specs"] = specs

        return phone

    async def enrich_phones_batch(
        self, phones: list[dict[str, Any]], max_concurrent: int = constants.KIMOVIL_MAX_CONCURRENT
    ) -> list[dict[str, Any]]:
        """
        Enrich multiple phones with specs (async batch)

        Args:
            phones: List of phone dicts
            max_concurrent: Max concurrent requests (keep low for Kimovil)

        Returns:
            List of enriched phone dicts
        """
        # Process in batches to respect rate limits
        tasks = [self.enrich_phone(phone) for phone in phones]
        return await asyncio.gather(*tasks)

    async def enrich_phone_list(self, phones: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich list of phones with Kimovil specs

        This is the main entry point called by AndroidAnalyzer.
        Uses Playwright scraper with caching and rate limiting.

        Args:
            phones: List of phone dicts with 'title' field

        Returns:
            List of phones with added 'kimovil_specs' field
        """
        logger.info(f"🔍 Enriching {len(phones)} phones with Kimovil specs...")

        if self.scraper is None:
            logger.warning("⚠️  Scraper not available, skipping enrichment")
            for phone in phones:
                phone["kimovil_specs"] = None
            return phones

        # Use batch method with low concurrency (be polite to Kimovil)
        enriched = await self.enrich_phones_batch(
            phones, max_concurrent=constants.KIMOVIL_MAX_CONCURRENT
        )

        # Count successes
        success_count = sum(1 for p in enriched if p.get("kimovil_specs"))
        success_rate = (success_count / len(enriched) * 100) if enriched else 0

        logger.info(
            f"✅ Enrichment complete: {success_count}/{len(enriched)} ({success_rate:.1f}%)"
        )

        # # Show cache stats
        # if hasattr(self.scraper, "get_cache_stats"):
        #     stats = self.scraper.get_cache_stats()
        #     logger.info(f"💾 Cache: {stats.get('successful', 0)} specs cached")

        return enriched

    def get_display_score_from_specs(self, specs: dict[str, Any] | None) -> tuple[int, list[str]]:
        """
        Calculate display score from Kimovil specs

        Args:
            specs: Kimovil specs dict

        Returns:
            (score, labels) tuple
        """
        if not specs:
            return 0, []

        score = 0
        labels = []

        # Display type scoring
        display_type = specs.get("display_type", "").upper()
        if "AMOLED" in display_type:
            score += 12
            labels.append("📱 AMOLED display")
        elif "OLED" in display_type:
            score += 11
            labels.append("📱 OLED display")
        elif "IPS" in display_type:
            score += 5
            labels.append("📱 IPS LCD display")

        # Refresh rate scoring
        refresh_rate = specs.get("refresh_rate")
        if refresh_rate:
            if refresh_rate >= constants.HZ_160:
                score += 8
                labels.append("⚡ 165Hz refresh")
            elif refresh_rate >= constants.HZ_144:
                score += 7
                labels.append("⚡ 144Hz refresh")
            elif refresh_rate >= constants.HZ_120:
                score += 6
                labels.append("⚡ 120Hz refresh")
            elif refresh_rate >= constants.HZ_90:
                score += 3
                labels.append("⚡ 90Hz refresh")

        return score, labels


# Example usage
async def main():
    """Example: Enrich phone listings"""
    enricher = SpecEnricher()

    phones = [
        {"title": "Samsung S23 Ultra 256GB", "price": 180000},
        {"title": "Xiaomi 14T Pro 512GB", "price": 250000},
        {"title": "Google Pixel 7a 128GB", "price": 150000},
    ]

    logger.info("🔍 Enriching phones with Kimovil specs...")
    enriched = await enricher.enrich_phones_batch(phones, max_concurrent=2)

    for phone in enriched:
        specs = phone.get("kimovil_specs")
        if specs:
            score, labels = enricher.get_display_score_from_specs(specs)
            logger.info(f"\n✅ {phone['title']}")
            logger.info(f"   Display: {specs.get('display_type')} {specs.get('refresh_rate')}Hz")
            logger.info(f"   Score: {score} points")
            logger.info(f"   Labels: {', '.join(labels)}")
        else:
            logger.info(f"\n❌ {phone['title']}: No specs found")


if __name__ == "__main__":
    asyncio.run(main())
