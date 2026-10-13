import json

from src.analysis.analyzer import listing_warnings
from src.core.async_scraper import ad_id, parse_ad_meta, parse_listing_totals


def test_reads_totals_from_prerendered_state():
    state = json.dumps({"listing": {"listing": {"totalElements": 1000, "totalPages": 25}}})
    html = f"<script>window.__PRERENDERED_STATE__ = {json.dumps(state)};\n</script>"
    assert parse_listing_totals(html) == (1000, 25)


def test_missing_state_returns_none():
    assert parse_listing_totals("<html></html>") is None


def test_ad_meta_reads_seller_type_and_city_by_ad_id():

    ads = [
        {
            "url": "https://www.olx.kz/d/obyavlenie/iphone-12-IDr8vab.html",
            "isBusiness": True,
            "location": {"cityName": "Алматы"},
        },
        {
            "url": "https://www.olx.kz/d/obyavlenie/xiaomi-IDpNRGT.html",
            "isBusiness": False,
            "location": {"cityName": "Байзерек"},
        },
    ]
    state = json.dumps({"listing": {"listing": {"ads": ads}}})
    meta = parse_ad_meta(f"window.__PRERENDERED_STATE__ = {json.dumps(state)};\n")
    assert meta["IDr8vab"] == {"is_business": True, "city": "Алматы"}
    assert meta["IDpNRGT"]["city"] == "Байзерек"
    assert ad_id("https://www.olx.kz/d/obyavlenie/x-IDpNRGT.html?reason=extended") == "IDpNRGT"


def test_shop_and_out_of_town_listings_get_warnings():

    assert listing_warnings({"is_business": False, "city": "Алматы"}) == []
    warnings = listing_warnings({"is_business": True, "city": "Байзерек"})
    assert len(warnings) == 2
    assert any("Байзерек" in w for w in warnings)
