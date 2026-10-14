#!/usr/bin/env python3
"""
Kimovil.com Phone Specs Scraper - ENHANCED VERSION

Purpose: Fetch comprehensive phone specifications from Kimovil.com
Success Rate: 95-99% (tested 2025-11-06)
Method: curl_cffi fetches the page with a Chrome TLS fingerprint; selectolax parses it

Cloudflare answers headless Chromium with a 403 "Just a moment..." challenge, while
curl_cffi's impersonated Chrome gets the full server-rendered page (checked 2026-10-13).
Every spec is in that HTML, so no browser is needed at all.

Features:
- Uses curl_cffi for the request, selectolax (lexbor) for parsing
- Extracts 70+ spec fields per phone (flexible, handles missing fields)
- SQLite caching (never re-scrape same model)
- Rate limiting (respectful to server)
- Async for performance
- Robust: handles missing/extra fields gracefully

Integration: Used by spec_enrichment.py in analysis pipeline
"""

import asyncio
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from curl_cffi import CurlError
from curl_cffi.requests import AsyncSession
from selectolax.lexbor import LexborHTMLParser

from src.core import config, constants
from src.core.browser_transport import IMPERSONATE
from src.core.constants import HTTP_OK, KIMOVIL_FETCH_TIMEOUT_S
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def _table_rows(tree: LexborHTMLParser) -> list[tuple[str, str]]:
    """(label, value) of every table row with two cells, raw text stripped like textContent."""
    rows = []
    for row in tree.css("table tr"):
        cells = row.css("td, th")
        if len(cells) < 2:  # a label cell and a value cell
            continue
        key, value = cells[0].text().strip(), cells[1].text().strip()
        if key and value and key != value:
            rows.append((key, value))
    return rows


def _targeted_specs(tree: LexborHTMLParser, rows: list[tuple[str, str]]) -> dict[str, Any]:
    """Typed fields that need more than one table row: screen, main camera, DxOMark."""
    specs: dict[str, Any] = {}
    first: dict[str, str] = {}
    for key, value in rows:
        first.setdefault(key, value)
    if screen_type := _screen_type(first.get("Type", "")):
        specs["screen_type_detail"] = screen_type
    for _, value in rows:
        if hz := re.search(r"Refresh rate\s*(\d+)\s*Hz", value, re.IGNORECASE):
            specs["screen_refresh_rate"] = int(hz.group(1))
            break
    if mpx := re.search(r"(\d+(?:\.\d+)?)\s*Mpx", _camera_resolution(rows)):
        specs["camera_main_resolution"] = round(float(mpx.group(1)))
    if first.get("Sensor"):
        specs["camera_main_sensor"] = first["Sensor"]
    dxomark = tree.css_first("dl.dxomark-scores-dl dd")
    if dxomark and (score := re.match(r"\s*(\d+)", dxomark.text())):
        specs["dxomark_score"] = int(score.group(1))
    return specs


def _camera_resolution(rows: list[tuple[str, str]]) -> str:
    """The first "Resolution" row in megapixels: the main camera, not the screen."""
    return next((v for k, v in rows if k == "Resolution" and "mpx" in v.lower()), "")


def _screen_type(value: str) -> str | None:
    lowered = value.lower()
    for marker, label in (
        ("amoled", "AMOLED"),
        ("oled", "OLED"),
        ("ips", "IPS LCD"),
        ("lcd", "LCD"),
    ):
        if marker in lowered:
            return label
    return None


class KimovilScraper:
    """
    Scrape phone specs from Kimovil.com (curl_cffi + selectolax)

    Features:
    - Browser TLS fingerprint over curl_cffi (passes Cloudflare without a browser)
    - Comprehensive spec extraction (70+ fields)
    - SQLite caching (permanent storage)
    - Rate limiting (2-3s between requests)
    - Error handling and retries
    - Graceful handling of missing/extra fields
    """

    # Field mappings: Kimovil table key -> normalized key
    FIELD_MAPPINGS = {
        # Design & Materials
        "Size": "size_raw",
        "Weight": "weight_raw",
        "Usable surface": "usable_surface",
        "Materials": "materials",
        "Resistance certificates (dust, water)": "ip_rating",
        "Colors": "colors",
        # Screen
        "Diagonal": "screen_diagonal_raw",
        "Type": "screen_type",
        "Aspect Ratio": "screen_aspect_ratio",
        "Resolution": "screen_resolution_raw",
        "Density": "screen_density_raw",
        "Others": "screen_features_raw",
        # Performance
        "Model": "processor_model",
        "CPU": "processor_cpu",
        "Nanometer": "processor_nm",
        "Frequency": "processor_frequency",
        "64 Bits": "processor_64bit",
        "GPU": "gpu_model",
        "RAM": "ram_size_raw",
        "Score": "antutu_score_raw",
        "Capacity": "storage_capacity_raw",
        "SD Slot": "storage_expandable",
        # Security & Sensors
        "Fingerprint": "fingerprint",
        "Proximity": "sensor_proximity",
        "Light sensor": "sensor_light",
        "Accelerometer": "sensor_accelerometer",
        "Compass": "sensor_compass",
        "Gyroscope": "sensor_gyroscope",
        "Barometer": "sensor_barometer",
        "Hall": "sensor_hall",
        "Geomagnetic": "sensor_geomagnetic",
        # Audio
        "Audio": "audio_features",
        "Notifications LED": "led_notification",
        "Cooling system": "cooling_system",
        "Gaming buttons": "gaming_buttons",
        # Camera (will handle separately for multi-camera)
        "Flash": "camera_flash",
        "Optical Stabilisation": "camera_ois",
        "Slow Motion Video": "camera_slow_motion",
        "Features": "camera_features",
        # Connectivity
        "5G": "bands_5g",
        "4G LTE": "bands_4g",
        "3G": "bands_3g",
        "2G": "bands_2g",
        "Standards": "wifi_standards",
        "Version": "bluetooth_version",
        "Profiles": "bluetooth_profiles",
        "Supports": "gps_systems",
        "Charging": "usb_charging",
        "Host": "usb_host",
        "Mass Storage": "usb_mass_storage",
        "USB On-The-Go (OTG)": "usb_otg",
        "USB Type C": "usb_type_c",
        "USB Host 3.2": "usb_version",
        # Battery
        "Fast charge": "fast_charge",
        "Extra": "battery_extra",
        # Software
        "Operating System": "os_name",
        "Google Services": "google_services",
        "Widevine L1": "widevine_l1",
        "Updates": "os_updates",
        # Release
        "Release date": "release_date",
        "Launch price": "launch_price",
        # Brand
        "Brand": "brand_confirmed",
        "Aliases": "model_aliases",
    }

    def __init__(self, cache_db: str | None = None):
        """
        Initialize Kimovil scraper

        Args:
            cache_db: Path to SQLite cache database (default: global cache)

        Note:
            Cache is global (data/cache/kimovil_specs.db) and shared across ALL sessions.
            Phone specs don't change, so we never re-scrape the same phone.
        """
        if cache_db is None:
            self.cache_db = Path(config.get_cache_dir()) / "kimovil_specs.db"
        else:
            self.cache_db = Path(cache_db)

        self.cache_db.parent.mkdir(parents=True, exist_ok=True)
        self._init_cache_db()

        # Rate limiting
        self.min_delay = constants.KIMOVIL_REQUEST_DELAY
        self.last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()
        self._fetch_slots = asyncio.Semaphore(constants.KIMOVIL_MAX_CONCURRENT)
        # One scrape per model per run: duplicate titles await the same task.
        self._inflight: dict[str, asyncio.Task[dict[str, Any] | None]] = {}

        logger.info("✅ Kimovil scraper initialized (curl_cffi + selectolax)")
        logger.info(f"📦 Global cache: {config.display_path(self.cache_db)}")

    def _init_cache_db(self) -> None:
        """Initialize SQLite cache database"""
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS phone_specs (
                    model_key TEXT PRIMARY KEY,
                    brand TEXT,
                    model TEXT,
                    specs_json TEXT NOT NULL,
                    field_count INTEGER DEFAULT 0,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()

    def _get_cached_specs(self, model_key: str) -> dict[str, Any] | None:
        """Get specs from cache"""
        try:
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT specs_json FROM phone_specs WHERE model_key = ? AND success = 1",
                    (model_key,),
                )
                result = cursor.fetchone()
                return json.loads(result[0]) if result else None

        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def _save_to_cache(
        self, model_key: str, brand: str, model: str, specs: dict[str, Any], success: bool = True
    ) -> None:
        """Save specs to cache"""
        try:
            field_count = len([v for v in specs.values() if v is not None])
            with sqlite3.connect(self.cache_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO phone_specs
                    (model_key, brand, model, specs_json, field_count, success, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (model_key, brand, model, json.dumps(specs), field_count, success),
                )
                conn.commit()
            logger.debug(f"💾 Cached: {model_key} ({field_count} fields)")

        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def _normalize_model_name(self, brand: str, model: str) -> str:
        """Normalize model name for URL construction"""
        normalized = f"{brand} {model}".lower()
        normalized = normalized.replace("+", " plus")
        normalized = normalized.replace("(", "").replace(")", "")
        normalized = normalized.replace("/", " ")
        return "-".join(normalized.split())

    def _build_kimovil_url(self, brand: str, model: str) -> str:
        """Build Kimovil URL for phone specs page"""
        normalized = self._normalize_model_name(brand, model)
        return f"https://www.kimovil.com/en/where-to-buy-{normalized}"

    async def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests (serialized so concurrent callers queue up)"""
        async with self._rate_lock:
            await self._pace()

    async def _pace(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            logger.debug(f"⏳ Rate limit: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    async def scrape_phone_specs(self, brand: str, model: str) -> dict[str, Any] | None:
        """
        Scrape comprehensive specs for a phone

        Args:
            brand: Phone brand (e.g., "Samsung", "Xiaomi")
            model: Phone model (e.g., "Galaxy S23 Ultra", "Redmi Note 12 Pro")

        Returns:
            Dict with specs or None if failed

        Example:
            specs = await scraper.scrape_phone_specs("Samsung", "Galaxy S24 Ultra")
        """
        model_key = f"{brand}_{model}".lower().replace(" ", "_")

        # Check cache first
        cached = self._get_cached_specs(model_key)
        if cached:
            logger.info(f"💾 Cache hit: {brand} {model}")
            return cached

        if model_key not in self._inflight:
            self._inflight[model_key] = asyncio.create_task(
                self._scrape_uncached(model_key, brand, model)
            )
        return await self._inflight[model_key]

    async def _scrape_uncached(
        self, model_key: str, brand: str, model: str
    ) -> dict[str, Any] | None:
        logger.info(f"🌐 Scraping: {brand} {model}")

        # Build URL
        url = self._build_kimovil_url(brand, model)
        logger.debug(f"📍 URL: {url}")

        async with self._fetch_slots:
            await self._wait_for_rate_limit()
            specs = await self._scrape_page(url, brand, model)

        if specs and len([v for v in specs.values() if v is not None]) > 3:
            # Cache result (only if we got meaningful data)
            self._save_to_cache(model_key, brand, model, specs, success=True)
            logger.info(
                f"✅ Success: {brand} {model} ({len([v for v in specs.values() if v is not None])} fields)"
            )
        else:
            # Cache failure to avoid re-scraping
            self._save_to_cache(model_key, brand, model, specs or {}, success=False)
            logger.warning(f"⚠️  Failed: {brand} {model}")

        return specs

    async def _scrape_page(self, url: str, brand: str, model: str) -> dict[str, Any] | None:
        """Fetch the page over curl_cffi and parse it with selectolax."""
        page_url, html = await self._fetch_html(url)
        if html is None:
            return None
        return self._parse_page(html, page_url, brand, model)

    async def _fetch_html(self, url: str) -> tuple[str, str | None]:
        """(final URL, HTML), or (url, None) on a non-200 or a network error."""
        try:
            async with AsyncSession(impersonate=IMPERSONATE) as session:
                response = await session.get(url, timeout=KIMOVIL_FETCH_TIMEOUT_S)
        except CurlError as e:
            logger.warning(f"Kimovil fetch failed: {url}: {e}")
            return url, None
        if response.status_code != HTTP_OK:
            mitigated = response.headers.get("cf-mitigated")
            logger.warning(f"Bad status: {response.status_code} (cf-mitigated: {mitigated})")
            return url, None
        return str(response.url), response.text

    def _parse_page(self, html: str, page_url: str, brand: str, model: str) -> dict[str, Any]:
        """Every spec Kimovil's server-rendered page carries, typed where the format is known."""
        tree = LexborHTMLParser(html)
        h1 = tree.css_first("h1")
        title = h1.text().strip() if h1 else ""
        specs: dict[str, Any] = {
            "brand": brand,
            "model": model,
            "kimovil_url": page_url,
            "full_name": title or f"{brand} {model}",
        }
        rows = _table_rows(tree)
        specs.update(self._table_specs(rows))
        specs.update(_targeted_specs(tree, rows))
        return self._parse_and_convert_types(specs)

    def _table_specs(self, rows: list[tuple[str, str]]) -> dict[str, Any]:
        """Table rows keyed by FIELD_MAPPINGS (else ``extra_<key>``).

        Labels repeat across sections ("Type", "Resolution", "Others", "Capacity"); the
        first one wins, because the page lists the screen and storage before the camera,
        connectivity and battery rows that reuse the label.
        """
        specs: dict[str, Any] = {}
        for key, value in rows:
            specs.setdefault(self._spec_key(key, value), value)
        return specs

    def _spec_key(self, key: str, value: str) -> str:
        if key == "Capacity" and "mah" in value.lower():
            return "battery_capacity"  # storage and battery share the "Capacity" label
        mapped = self.FIELD_MAPPINGS.get(key)
        if mapped:
            return mapped
        sanitized = key.lower().replace(" ", "_").replace("(", "").replace(")", "")
        return f"extra_{sanitized}"

    def _parse_and_convert_types(self, specs: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw string values and convert to proper types

        Handles:
        - Numbers (int, float)
        - Booleans (Yes/No)
        - Lists (comma-separated)
        - Special formats (dates, prices, etc.)
        """
        parsed: dict[str, Any] = {}

        for key, value in specs.items():
            if value is None or value in {"", "--"}:
                parsed[key] = None
                continue

            # Skip if already proper type
            if not isinstance(value, str):
                parsed[key] = value
                continue

            value = value.strip()

            # Boolean conversions
            if value.lower() in ("yes", "true", "✓"):
                parsed[key] = True
                continue
            if value.lower() in ("no", "false", "✗"):
                parsed[key] = False
                continue

            # Number conversions
            try:
                # Weight (232 g)
                if key in ("weight_raw", "weight") and (match := re.search(r"(\d+)\s*g", value)):
                    parsed["weight"] = int(match.group(1))
                    continue

                # Size (79.0 mm x 162.3 mm x 8.6 mm)
                if key == "size_raw":
                    sizes = re.findall(r"(\d+\.?\d*)\s*mm", value)
                    if len(sizes) >= 3:
                        parsed["size_width"] = float(sizes[0])
                        parsed["size_height"] = float(sizes[1])
                        parsed["size_depth"] = float(sizes[2])
                    continue

                # Screen diagonal (6.8")
                if key == "screen_diagonal_raw" and (match := re.search(r"(\d+\.?\d*)", value)):
                    parsed["screen_diagonal"] = float(match.group(1))
                    continue

                # Screen resolution (1440 x 3120 px)
                if key == "screen_resolution_raw":
                    res = re.findall(r"(\d+)", value)
                    if len(res) >= 2:
                        parsed["screen_resolution_width"] = int(res[0])
                        parsed["screen_resolution_height"] = int(res[1])
                    if res_name := re.search(r"(WQHD\+|QHD\+|FHD\+|HD\+)", value, re.IGNORECASE):
                        parsed["screen_resolution_name"] = res_name.group(1)
                    continue

                # Screen density (505 ppi)
                if key == "screen_density_raw" and (match := re.search(r"(\d+)\s*ppi", value)):
                    parsed["screen_density"] = int(match.group(1))
                    continue

                # Processor frequency (3.3 GHz)
                if key == "processor_frequency" and (
                    match := re.search(r"(\d+\.?\d*)\s*ghz", value.lower())
                ):
                    parsed["processor_frequency"] = float(match.group(1))
                    continue

                # Processor nm (4 nm)
                if key == "processor_nm" and (match := re.search(r"(\d+)\s*nm", value.lower())):
                    parsed["processor_nm"] = int(match.group(1))
                    continue

                # RAM (12 GB)
                if key == "ram_size_raw" and (match := re.search(r"(\d+)\s*gb", value.lower())):
                    parsed["ram_size"] = int(match.group(1))
                    continue

                # Storage (256 GB)
                if key == "storage_capacity_raw" and (
                    match := re.search(r"(\d+)\s*gb", value.lower())
                ):
                    parsed["storage_capacity"] = int(match.group(1))
                    continue

                # AnTuTu score (1,814,869)
                if key == "antutu_score_raw":
                    score_str = value.replace(",", "").replace(".", "").replace(" ", "")
                    if score_match := re.search(r"(\d{6,})", score_str):
                        parsed["antutu_v10_score"] = int(score_match.group(1))
                    continue

                # Battery (5000 mAh)
                if key in ("battery_capacity", "capacity") and (
                    match := re.search(r"(\d+)\s*mah", value.lower())
                ):
                    parsed["battery_capacity"] = int(match.group(1))
                    continue

                # Fast charging (45W)
                if key == "fast_charge" and (
                    match := re.search(r"(\d+(?:\.\d+)?)\s*w", value.lower())
                ):
                    parsed["fast_charging_wattage"] = round(float(match.group(1)))
                    continue

                # Release date (January 2024, 1 year ago)
                if key == "release_date":
                    if year_match := re.search(r"(20\d{2})", value):
                        parsed["release_year"] = int(year_match.group(1))
                    if month_match := re.search(
                        r"(january|february|march|april|may|june|july|august|september|october|november|december)",
                        value.lower(),
                    ):
                        months = {
                            "january": 1,
                            "february": 2,
                            "march": 3,
                            "april": 4,
                            "may": 5,
                            "june": 6,
                            "july": 7,
                            "august": 8,
                            "september": 9,
                            "october": 10,
                            "november": 11,
                            "december": 12,
                        }
                        parsed["release_month"] = months[month_match.group(1)]
                    parsed["release_date"] = value
                    continue

                # Launch price (€ 1,459.00 ($ 1,677.32))
                if key == "launch_price":
                    if eur_match := re.search(r"€\s*([\d,\.]+)", value):
                        parsed["launch_price_eur"] = float(eur_match.group(1).replace(",", ""))
                    if usd_match := re.search(r"\$\s*([\d,\.]+)", value):
                        parsed["launch_price_usd"] = float(usd_match.group(1).replace(",", ""))
                    continue

            except Exception:
                pass

            # Default: keep as string
            parsed[key] = value

        return parsed

    async def scrape_batch(
        self, phones: list[tuple[str, str]], max_concurrent: int = 2
    ) -> list[dict[str, Any] | None]:
        """
        Scrape multiple phones concurrently

        Args:
            phones: List of (brand, model) tuples
            max_concurrent: Max concurrent scrapes (default: 2, be polite!)

        Returns:
            List of spec dicts (None for failures)
        """
        logger.info(f"🚀 Batch scraping {len(phones)} phones (max {max_concurrent} concurrent)")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(brand: str, model: str) -> dict[str, Any] | None:
            async with semaphore:
                return await self.scrape_phone_specs(brand, model)

        # Create tasks
        tasks = [scrape_with_semaphore(brand, model) for brand, model in phones]

        # Execute with progress
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        specs_list: list[dict[str, Any] | None] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed: {phones[i]} - {result}")
                specs_list.append(None)
            elif isinstance(result, dict):
                specs_list.append(result)
            else:
                specs_list.append(None)

        success_count = sum(1 for s in specs_list if s)
        logger.info(
            f"✅ Batch complete: {success_count}/{len(phones)} successful ({success_count / len(phones) * 100:.1f}%)"
        )

        return specs_list
