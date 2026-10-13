#!/usr/bin/env python3
"""
Re-categorize ALL listings with improved brand detection
"""

import json
from pathlib import Path

# Import session directory management (from project root)
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from src.core.config import get_results_dir
from src.detection.patterns import detect_phone_brand
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def detect_phone_brand_improved(text):
    """Enhanced brand detection - uses centralized improved patterns"""
    brand, phone_type, score = detect_phone_brand(text)
    if brand != "unknown":
        logger.debug(f"Detected: {brand} | Type: {phone_type} | Score: {score}")
    return brand, phone_type


def main():  # noqa: PLR0915
    logger.info("📂 RE-CATEGORIZE ALL LISTINGS Improved brand detection with better typo handling")

    # Load improved data from SESSION directory
    results_dir = get_results_dir()
    data_file = results_dir / "all_listings.json"

    if not data_file.exists():
        logger.error(f"File not found: {data_file}")
        logger.warning("Please run the scraper first!")
        logger.warning(f"Expected file at: {data_file}")
        return

    with Path.open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    all_listings = data["listings"]
    logger.info(f"Loaded {len(all_listings)} listings for re-categorization")

    # Re-categorize all
    iphones = []
    androids = []
    unknown = []

    logger.info("RE-CATEGORIZING LISTINGS")

    # Use tqdm for progress visualization
    with logging_redirect_tqdm():
        for listing in tqdm(
            all_listings,
            desc="🔄 Re-categorizing",
            unit="listing",
            colour="cyan",
            smoothing=0.1,
            leave=False,
            position=0,
            dynamic_ncols=True,
        ):
            brand, phone_type = detect_phone_brand_improved(listing["title"])

            listing["detected_brand"] = brand
            listing["phone_type"] = phone_type

            if phone_type == "iphone":
                iphones.append(listing)
            elif phone_type == "android":
                androids.append(listing)
            else:
                unknown.append(listing)

    logger.info("IMPROVED CATEGORIZATION RESULTS")

    total = len(all_listings)
    logger.info(f"Total Listings: {total}")
    logger.info(f"iPhones {len(iphones)} ({len(iphones) / total * 100:.1f}%)")
    logger.info(f"Android {len(androids)} ({len(androids) / total * 100:.1f}%)")
    logger.info(f"Unknown {len(unknown)} ({len(unknown) / total * 100:.1f}%)")

    # Save updated data to SESSION directory
    results_dir = get_results_dir()
    logger.info(f"\n💾 Saving updated categorization to: {results_dir}")

    with Path.open(results_dir / "all_listings.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": len(all_listings),
                "scraped_at": data["scraped_at"],
                "listings": all_listings,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with Path.open(results_dir / "iphones.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(iphones), "phones": iphones}, f, ensure_ascii=False, indent=2)

    with Path.open(results_dir / "androids.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(androids), "phones": androids}, f, ensure_ascii=False, indent=2)

    with Path.open(results_dir / "unknown.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(unknown), "phones": unknown}, f, ensure_ascii=False, indent=2)

    logger.success("Updated files saved successfully!")

    # Android brand breakdown
    logger.info("ANDROID BRAND BREAKDOWN")
    brands = {}
    for listing in androids:
        brand = listing.get("detected_brand", "unknown")
        brands[brand] = brands.get(brand, 0) + 1

    for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  • {brand:15s}: {count:3d} phones")

    # Show remaining unknown
    if unknown:
        logger.info(f"STILL UNKNOWN ({len(unknown)})")
        for i, item in enumerate(unknown[:15], 1):
            logger.info(f"  {i:2d}. {item['title'][:75]}")
            logger.debug(f"      Price: {item['price']:,} KZT | {item['link']}")
