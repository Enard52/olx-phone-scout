import asyncio
import time
from itertools import pairwise

from src.enrichment.kimovil_scraper import KimovilScraper


def test_duplicates_scrape_once_and_requests_are_paced(tmp_path):
    scraper = KimovilScraper(cache_db=str(tmp_path / "specs.db"))
    scraper.min_delay = 0.05
    starts: list[float] = []

    async def fake_scrape(url, brand, model):
        starts.append(time.monotonic())
        await asyncio.sleep(0.01)

    scraper._scrape_page = fake_scrape

    async def run():
        models = ["Galaxy S22"] * 5 + ["Galaxy S21"] * 5 + ["Galaxy A56"] * 5
        await asyncio.gather(*(scraper.scrape_phone_specs("Samsung", m) for m in models))

    asyncio.run(run())

    assert len(starts) == 3
    gaps = [b - a for a, b in pairwise(starts)]
    assert all(gap >= 0.04 for gap in gaps), gaps
