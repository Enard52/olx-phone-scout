#!/usr/bin/env python3
"""
Centralized Configuration for OLX Phone Analyzer

Easy-to-modify settings for scraping, filtering, and analysis.
Just edit the values below and run your scripts!
"""

import json
from datetime import datetime as dt
from pathlib import Path

from src.core.constants import MAX_CONFIDENCE_SCORE, MIN_CONFIDENCE_SCORE
from src.infrastructure.logging import logger

# =============================================================================
# SCRAPING SETTINGS
# =============================================================================

# Target location on OLX.kz
# Options: 'alma-ata', 'astana', 'shymkent', 'karaganda', 'aktobe', etc.
LOCATION = "alma-ata"
# City the user lives in: listings elsewhere (e.g. with LOCATION = "alm") get a warning
HOME_CITY = "Алматы"

# Include shops/resellers (OLX "business" sellers); off = private sellers only
INCLUDE_BUSINESS = False

# Price range in KZT
MIN_PRICE = 90000
MAX_PRICE = 380000

# How many pages to scrape (each page has ~15-20 listings)
MAX_PAGES = 25

# How far back to search (in days)
# Note: OLX might not have exact timeline control, but we try
DAYS_BACK = 25

# Delay between page requests (in seconds) - be respectful!
REQUEST_DELAY = 1.5

# Request timeout (in seconds)
REQUEST_TIMEOUT = 15

ASYNC_MAX_CONCURRENCY = 10

# =============================================================================
# PHONE TYPE FILTERING
# =============================================================================

# What types of phones to analyze?
# Options: 'both', 'android', 'iphone'
PHONE_TYPE_FILTER = "android"

# Minimum brand confidence score (0-100)
# Lower = more inclusive but might include false positives
MIN_BRAND_CONFIDENCE = 50


# =============================================================================
# ANALYSIS SETTINGS
# =============================================================================

# How many top recommendations to save
TOP_RECOMMENDATIONS_COUNT = 50  # More results for flagship comparison

# Show phones with market price data only?
# If True, only analyze phones we have price data for
# If False, analyze all phones (use heuristics for unknown models)
REQUIRE_MARKET_DATA = False

# Minimum value score to include in recommendations (0-100)
MIN_VALUE_SCORE = 50


# =============================================================================
# LOGGING SETTINGS
# =============================================================================

# Log level: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
LOG_LEVEL = "DEBUG"

# Maximum log file size (in MB)
MAX_LOG_FILE_SIZE = 50

# Number of log backup files to keep (total = MAX_LOG_FILE_SIZE * MAX_LOG_BACKUPS)
MAX_LOG_BACKUPS = 20  # 20 files x 10MB = 200MB max

# How many days to keep old logs
LOG_RETENTION_DAYS = 7


# =============================================================================
# FILE PATHS & SESSION MANAGEMENT
# =============================================================================

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"


def display_path(path: str | Path) -> Path:
    """Path relative to the repo root for console output; paths outside the repo stay as is."""
    p = Path(path)
    try:
        return p.relative_to(BASE_DIR)
    except ValueError:
        return p


def get_readable_timestamp():
    """Get human-readable timestamp: 2025-10-28_14-30-52"""
    return dt.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_compact_timestamp():
    """Get compact timestamp for filenames: 20251028_143052"""
    return dt.now().strftime("%Y%m%d_%H%M%S")


def get_session_name():
    """
    Generate session name based on current configuration (NO timestamp)
    Format: alma-ata_130k-350k_both
    Same config = same session folder (no duplication)
    """
    price_range = f"{MIN_PRICE // 1000}k-{MAX_PRICE // 1000}k"

    parts = [LOCATION, price_range, PHONE_TYPE_FILTER]
    if INCLUDE_BUSINESS:
        parts.append("shops")

    return "_".join(parts)


def get_session_dir():
    """Get or create session directory for current run"""
    session_name = get_session_name()
    session_dir = DATA_DIR / "sessions" / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


# Session directories (created dynamically per run)
def get_results_dir():
    """Get results directory for current session"""
    results_dir = get_session_dir() / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def get_reports_dir():
    """Get reports directory for current session"""
    reports_dir = get_session_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def get_logs_dir():
    """Get logs directory for current session"""
    logs_dir = get_session_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_cache_dir():
    """
    Get global cache directory (shared across ALL sessions)

    Phone specs don't change, so we cache them globally.
    All sessions use the same cache database.

    Location: data/cache/
    """
    cache_dir = DATA_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# Legacy directories (deprecated - no longer created)
# Use get_results_dir() and get_reports_dir() instead
RESULTS_DIR = DATA_DIR / "results"
REPORTS_DIR = DATA_DIR / "reports"
# RESULTS_DIR.mkdir(parents=True, exist_ok=True)  # Commented out - use sessions
# REPORTS_DIR.mkdir(parents=True, exist_ok=True)  # Commented out - use sessions


# Output file names (with timestamp)
def get_output_files():
    """Get output file paths for current session"""
    results_dir = get_results_dir()
    reports_dir = get_reports_dir()
    timestamp = get_compact_timestamp()

    return {
        "all_listings": results_dir / "all_listings.json",
        "iphones": results_dir / "iphones.json",
        "androids": results_dir / "androids.json",
        "unknown": results_dir / "unknown.json",
        "analyzed_androids": results_dir / "androids_analyzed.json",
        "top_androids": results_dir / f"TOP_{TOP_RECOMMENDATIONS_COUNT}_ANDROID.json",
        "recommendations_report": reports_dir / f"TOP_RECOMMENDATIONS_{timestamp}.txt",
        "session_info": get_session_dir() / "session_info.json",
    }


# Backwards compatibility - use legacy paths by default
ALL_LISTINGS_FILE = RESULTS_DIR / "all_listings_improved.json"
IPHONES_FILE = RESULTS_DIR / "iphones_all.json"
ANDROIDS_FILE = RESULTS_DIR / "androids_all.json"
UNKNOWN_FILE = RESULTS_DIR / "unknown_final.json"
ANALYZED_ANDROIDS_FILE = RESULTS_DIR / "androids_analyzed.json"
TOP_ANDROIDS_FILE = RESULTS_DIR / "TOP_30_ANDROID.json"
RECOMMENDATIONS_REPORT = REPORTS_DIR / "TOP_ANDROID_RECOMMENDATIONS.txt"


# =============================================================================
# OLX.KZ SPECIFIC SETTINGS
# =============================================================================

# Base URL for OLX Kazakhstan
OLX_BASE_URL = "https://www.olx.kz"

# Category path for mobile phones
# Full path: {OLX_BASE_URL}/elektronika/telefony-i-aksesuary/mobilnye-telefony-smartfony/{LOCATION}/
CATEGORY_PATH = "elektronika/telefony-i-aksesuary/mobilnye-telefony-smartfony"

# Search parameters
SEARCH_PARAMS = {
    "search[private_business]": "private",  # Only private sellers (exclude shops)
    "search[order]": "created_at:desc",  # Sort by newest first
}

# User agent for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_search_url():
    """Get the base search URL (price filter added by scraper via params)"""
    return f"{OLX_BASE_URL}/{CATEGORY_PATH}/{LOCATION}/"


def get_price_range_display():
    """Get human-readable price range"""
    return f"{MIN_PRICE:,} - {MAX_PRICE:,} KZT"


def get_config_summary():
    """Get a summary of current configuration"""
    return {
        "Location": AVAILABLE_LOCATIONS.get(LOCATION, LOCATION),
        "Sellers": "private + shops" if INCLUDE_BUSINESS else "private only",
        "Price Range": get_price_range_display(),
        "Phone Type": PHONE_TYPE_FILTER.upper(),
        "Max Pages": MAX_PAGES,
        "Days Back": DAYS_BACK,
        "Top Results": TOP_RECOMMENDATIONS_COUNT,
        "Log Level": LOG_LEVEL,
    }


def print_config():
    """Print current configuration in a nice format"""
    logger.info("\n" + "=" * 80)
    logger.info("CURRENT CONFIGURATION")
    logger.info("=" * 80)

    config = get_config_summary()
    max_key_length = max(len(k) for k in config)

    for key, value in config.items():
        logger.info(f"  {key:<{max_key_length}} : {value}")

    logger.info("=" * 80 + "\n")


def validate_config():
    """Validate configuration settings"""
    errors = []

    if MIN_PRICE >= MAX_PRICE:
        errors.append("MIN_PRICE must be less than MAX_PRICE")

    if MIN_PRICE < 0 or MAX_PRICE < 0:
        errors.append("Prices must be positive")

    if MAX_PAGES < 1:
        errors.append("MAX_PAGES must be at least 1")

    if DAYS_BACK < 1:
        errors.append("DAYS_BACK must be at least 1")

    if PHONE_TYPE_FILTER not in ["both", "android", "iphone"]:
        errors.append("PHONE_TYPE_FILTER must be 'both', 'android', or 'iphone'")

    if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        errors.append("LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR")

    if MIN_BRAND_CONFIDENCE < MIN_CONFIDENCE_SCORE or MIN_BRAND_CONFIDENCE > MAX_CONFIDENCE_SCORE:
        errors.append(
            f"MIN_BRAND_CONFIDENCE must be between {MIN_CONFIDENCE_SCORE} and {MAX_CONFIDENCE_SCORE}"
        )

    if TOP_RECOMMENDATIONS_COUNT < 1:
        errors.append("TOP_RECOMMENDATIONS_COUNT must be at least 1")

    if errors:
        logger.error("\n❌ Configuration Errors:")
        for error in errors:
            logger.error(f"  • {error}")
        return False

    return True


# =============================================================================
# LOCATION MAPPING
# =============================================================================

# Available cities on OLX.kz
AVAILABLE_LOCATIONS = {
    "alma-ata": "Almaty",
    "alm": "Almaty Region (city + oblast)",
    "astana": "Astana (Nur-Sultan)",
    "shymkent": "Shymkent",
    "karaganda": "Karaganda",
    "aktobe": "Aktobe",
    "taraz": "Taraz",
    "pavlodar": "Pavlodar",
    "ust-kamenogorsk": "Ust-Kamenogorsk",
    "semey": "Semey",
    "kostanay": "Kostanay",
    "kyzylorda": "Kyzylorda",
    "atyrau": "Atyrau",
    "petropavlovsk": "Petropavlovsk",
    "oral": "Oral",
    "temirtau": "Temirtau",
    "aktau": "Aktau",
    "kokshetau": "Kokshetau",
    "turkestan": "Turkestan",
}


def list_available_locations():
    """Print all available locations"""
    logger.info("\n" + "=" * 80)
    logger.info("AVAILABLE LOCATIONS")
    logger.info("=" * 80)
    for slug, name in sorted(AVAILABLE_LOCATIONS.items(), key=lambda x: x[1]):
        current = " ← CURRENT" if slug == LOCATION else ""
        logger.info(f"  {slug:20s} → {name}{current}")
    logger.info("=" * 80 + "\n")


def save_session_info():
    """Save current session configuration to file"""
    output_files = get_output_files()
    session_info = {
        "timestamp": get_readable_timestamp(),
        "session_name": get_session_name(),
        "configuration": get_config_summary(),
        "location": LOCATION,
        "location_name": AVAILABLE_LOCATIONS.get(LOCATION, LOCATION),
        "price_range": {
            "min": MIN_PRICE,
            "max": MAX_PRICE,
        },
        "phone_type_filter": PHONE_TYPE_FILTER,
        "scraping": {
            "max_pages": MAX_PAGES,
            "days_back": DAYS_BACK,
        },
        "output_files": {k: str(v) for k, v in output_files.items()},
    }

    with Path.open(output_files["session_info"], "w", encoding="utf-8") as f:
        json.dump(session_info, f, ensure_ascii=False, indent=2)

    return output_files["session_info"]


if __name__ == "__main__":
    # Test configuration
    print_config()

    if validate_config():
        logger.success("✅ Configuration is valid!\n")
        list_available_locations()
        logger.info(f"\n📍 Search URL: {get_search_url()}")
        logger.info(f"\n📁 Session Directory: {display_path(get_session_dir())}")
        logger.info(f"📝 Session Name: {get_session_name()}\n")
    else:
        logger.error("❌ Please fix configuration errors above.\n")
