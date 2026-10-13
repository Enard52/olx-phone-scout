import asyncio

from src.enrichment import kimovil_scraper
from src.enrichment.kimovil_scraper import KimovilScraper


class _ChallengeSession:
    """curl_cffi stand-in that gets Cloudflare's challenge instead of the page."""

    def __init__(self, impersonate):
        self.impersonate = impersonate

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, timeout):
        return type("R", (), {"status_code": 403, "headers": {"cf-mitigated": "challenge"}})()


def test_a_challenged_fetch_returns_no_specs(tmp_path, monkeypatch):
    monkeypatch.setattr(kimovil_scraper, "AsyncSession", _ChallengeSession)
    scraper = KimovilScraper(cache_db=str(tmp_path / "specs.db"))

    specs = asyncio.run(scraper._scrape_page("https://kimovil.test/x", "Samsung", "S23"))

    assert specs is None
