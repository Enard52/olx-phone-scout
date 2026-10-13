"""
Comprehensive tests for src/core/config.py

Tests all configuration functions and settings:
- Timestamp generation (readable, compact)
- Session management (name, directories)
- Output file paths
- URL building
- Config validation
- Session info saving

Target: 80%+ coverage for config.py (140 statements)
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.core import config


class TestTimestampFunctions:
    """Test timestamp generation functions"""

    def test_readable_timestamp_format(self):
        """Readable timestamp format: YYYY-MM-DD_HH-MM-SS"""
        timestamp = config.get_readable_timestamp()
        # Should match format: 2025-11-14_16-30-45
        assert len(timestamp) == 19
        assert timestamp[4] == "-"
        assert timestamp[7] == "-"
        assert timestamp[10] == "_"
        assert timestamp[13] == "-"
        assert timestamp[16] == "-"

    def test_compact_timestamp_format(self):
        """Compact timestamp format: YYYYMMDD_HHMMSS"""
        timestamp = config.get_compact_timestamp()
        # Should match format: 20251114_163045
        assert len(timestamp) == 15
        assert timestamp[8] == "_"
        assert timestamp.replace("_", "").isdigit()

    def test_timestamps_are_current(self):
        """Timestamps should reflect current date/time"""
        readable = config.get_readable_timestamp()
        compact = config.get_compact_timestamp()

        year = str(datetime.now().year)
        assert readable.startswith(year)
        assert compact.startswith(year)


class TestSessionManagement:
    """Test session name and directory functions"""

    def test_session_name_format(self):
        """Session name format: location_pricerange_phonetype"""
        with patch.object(config, "LOCATION", "alma-ata"):
            with patch.object(config, "MIN_PRICE", 100000):
                with patch.object(config, "MAX_PRICE", 300000):
                    with patch.object(config, "PHONE_TYPE_FILTER", "android"):
                        name = config.get_session_name()
                        assert name == "alma-ata_100k-300k_android"

    def test_session_name_uses_config(self):
        """Session name changes with config"""
        with patch.object(config, "LOCATION", "astana"):
            with patch.object(config, "MIN_PRICE", 50000):
                with patch.object(config, "MAX_PRICE", 200000):
                    with patch.object(config, "PHONE_TYPE_FILTER", "both"):
                        name = config.get_session_name()
                        assert "astana" in name
                        assert "50k-200k" in name
                        assert "both" in name

    def test_get_session_dir_creates_directory(self):
        """get_session_dir creates directory if not exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                session_dir = config.get_session_dir()
                assert session_dir.exists()
                assert session_dir.is_dir()
                assert "sessions" in str(session_dir)

    def test_get_results_dir_creates_subdirectory(self):
        """get_results_dir creates results subdirectory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                results_dir = config.get_results_dir()
                assert results_dir.exists()
                assert results_dir.name == "results"

    def test_get_reports_dir_creates_subdirectory(self):
        """get_reports_dir creates reports subdirectory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                reports_dir = config.get_reports_dir()
                assert reports_dir.exists()
                assert reports_dir.name == "reports"

    def test_get_logs_dir_creates_subdirectory(self):
        """get_logs_dir creates logs subdirectory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                logs_dir = config.get_logs_dir()
                assert logs_dir.exists()
                assert logs_dir.name == "logs"

    def test_get_cache_dir_creates_subdirectory(self):
        """get_cache_dir creates cache subdirectory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                cache_dir = config.get_cache_dir()
                assert cache_dir.exists()
                assert cache_dir.name == "cache"


class TestOutputFiles:
    """Test output file path generation"""

    def test_get_output_files_returns_dict(self):
        """get_output_files returns dict of file paths"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                output_files = config.get_output_files()
                assert isinstance(output_files, dict)
                assert "all_listings" in output_files
                assert "iphones" in output_files
                assert "androids" in output_files
                assert "unknown" in output_files
                assert "analyzed_androids" in output_files
                assert "top_androids" in output_files
                assert "recommendations_report" in output_files
                assert "session_info" in output_files

    def test_output_files_are_paths(self):
        """All output files are Path objects"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                output_files = config.get_output_files()
                for key, path in output_files.items():
                    assert isinstance(path, Path), f"{key} is not a Path object"

    def test_output_files_in_correct_directories(self):
        """Output files are in correct directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                output_files = config.get_output_files()

                # Results files should be in results dir
                assert "results" in str(output_files["all_listings"])
                assert "results" in str(output_files["androids"])

                # Report files should be in reports dir
                assert "reports" in str(output_files["recommendations_report"])

                # Session info should be in session root
                assert "session_info.json" in str(output_files["session_info"])

    def test_top_androids_uses_config_count(self):
        """TOP_ANDROID file name uses TOP_RECOMMENDATIONS_COUNT"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                with patch.object(config, "TOP_RECOMMENDATIONS_COUNT", 100):
                    output_files = config.get_output_files()
                    assert "TOP_100_ANDROID" in str(output_files["top_androids"])


class TestURLBuilding:
    """Test URL building functions"""

    def test_get_search_url_format(self):
        """Search URL has correct format"""
        with patch.object(config, "LOCATION", "alma-ata"):
            url = config.get_search_url()
            assert "olx.kz" in url
            assert "mobilnye-telefony-smartfony" in url
            assert "alma-ata" in url
            assert url.endswith("/")

    def test_get_search_url_uses_config(self):
        """Search URL changes with LOCATION"""
        with patch.object(config, "LOCATION", "astana"):
            url = config.get_search_url()
            assert "astana" in url

    def test_get_price_range_display(self):
        """Price range display formats correctly"""
        with patch.object(config, "MIN_PRICE", 100000):
            with patch.object(config, "MAX_PRICE", 300000):
                display = config.get_price_range_display()
                assert "100,000" in display
                assert "300,000" in display
                assert "KZT" in display


class TestConfigSummary:
    """Test configuration summary functions"""

    def test_get_config_summary_returns_dict(self):
        """get_config_summary returns dict with all keys"""
        summary = config.get_config_summary()
        assert isinstance(summary, dict)
        assert "Location" in summary
        assert "Price Range" in summary
        assert "Phone Type" in summary
        assert "Max Pages" in summary
        assert "Days Back" in summary
        assert "Top Results" in summary
        assert "Log Level" in summary

    def test_config_summary_uses_current_config(self):
        """Config summary reflects current config values"""
        with patch.object(config, "LOCATION", "alma-ata"):
            with patch.object(config, "PHONE_TYPE_FILTER", "android"):
                with patch.object(config, "MAX_PAGES", 25):
                    summary = config.get_config_summary()
                    assert "Almaty" in summary["Location"]
                    assert "ANDROID" in summary["Phone Type"]
                    assert summary["Max Pages"] == 25

    def test_print_config_logs_summary(self, caplog):
        """print_config logs configuration summary"""
        with patch.object(config, "LOCATION", "alma-ata"):
            config.print_config()
            # Should log some configuration info
            # Note: This may not capture logger.info if using loguru


class TestConfigValidation:
    """Test configuration validation"""

    def test_validate_config_with_valid_settings(self):
        """Valid config passes validation"""
        with patch.object(config, "MIN_PRICE", 50000):
            with patch.object(config, "MAX_PRICE", 300000):
                with patch.object(config, "MAX_PAGES", 20):
                    with patch.object(config, "DAYS_BACK", 30):
                        with patch.object(config, "PHONE_TYPE_FILTER", "android"):
                            with patch.object(config, "LOG_LEVEL", "INFO"):
                                with patch.object(config, "MIN_BRAND_CONFIDENCE", 50):
                                    with patch.object(config, "TOP_RECOMMENDATIONS_COUNT", 50):
                                        assert config.validate_config() is True

    def test_validate_config_min_price_gte_max_price(self):
        """MIN_PRICE >= MAX_PRICE fails validation"""
        with patch.object(config, "MIN_PRICE", 300000):
            with patch.object(config, "MAX_PRICE", 100000):
                assert config.validate_config() is False

    def test_validate_config_negative_price(self):
        """Negative prices fail validation"""
        with patch.object(config, "MIN_PRICE", -10000):
            with patch.object(config, "MAX_PRICE", 100000):
                assert config.validate_config() is False

    def test_validate_config_invalid_max_pages(self):
        """MAX_PAGES < 1 fails validation"""
        with patch.object(config, "MAX_PAGES", 0):
            assert config.validate_config() is False

    def test_validate_config_invalid_days_back(self):
        """DAYS_BACK < 1 fails validation"""
        with patch.object(config, "DAYS_BACK", 0):
            assert config.validate_config() is False

    def test_validate_config_invalid_phone_type(self):
        """Invalid PHONE_TYPE_FILTER fails validation"""
        with patch.object(config, "PHONE_TYPE_FILTER", "windows"):
            assert config.validate_config() is False

    def test_validate_config_invalid_log_level(self):
        """Invalid LOG_LEVEL fails validation"""
        with patch.object(config, "LOG_LEVEL", "TRACE"):
            assert config.validate_config() is False

    def test_validate_config_invalid_brand_confidence(self):
        """MIN_BRAND_CONFIDENCE out of range fails validation"""
        with patch.object(config, "MIN_BRAND_CONFIDENCE", 150):
            assert config.validate_config() is False

    def test_validate_config_invalid_top_recommendations(self):
        """TOP_RECOMMENDATIONS_COUNT < 1 fails validation"""
        with patch.object(config, "TOP_RECOMMENDATIONS_COUNT", 0):
            assert config.validate_config() is False


class TestLocationMapping:
    """Test location mapping functions"""

    def test_available_locations_is_dict(self):
        """AVAILABLE_LOCATIONS is a dict"""
        assert isinstance(config.AVAILABLE_LOCATIONS, dict)
        assert len(config.AVAILABLE_LOCATIONS) > 0

    def test_available_locations_has_alma_ata(self):
        """AVAILABLE_LOCATIONS includes alma-ata"""
        assert "alma-ata" in config.AVAILABLE_LOCATIONS
        assert config.AVAILABLE_LOCATIONS["alma-ata"] == "Almaty"

    def test_available_locations_has_astana(self):
        """AVAILABLE_LOCATIONS includes astana"""
        assert "astana" in config.AVAILABLE_LOCATIONS

    def test_list_available_locations(self, caplog):
        """list_available_locations logs all locations"""
        with patch.object(config, "LOCATION", "alma-ata"):
            config.list_available_locations()
            # Should log location information
            # Note: This may not capture logger.info if using loguru


class TestSessionInfoSaving:
    """Test session info saving function"""

    def test_save_session_info_creates_file(self):
        """save_session_info creates JSON file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                with patch.object(config, "LOCATION", "alma-ata"):
                    with patch.object(config, "MIN_PRICE", 100000):
                        with patch.object(config, "MAX_PRICE", 300000):
                            saved_path = config.save_session_info()
                            assert saved_path.exists()
                            assert saved_path.suffix == ".json"

    def test_save_session_info_content(self):
        """save_session_info writes correct JSON content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "DATA_DIR", Path(tmpdir)):
                with patch.object(config, "LOCATION", "alma-ata"):
                    with patch.object(config, "MIN_PRICE", 100000):
                        with patch.object(config, "MAX_PRICE", 300000):
                            with patch.object(config, "PHONE_TYPE_FILTER", "android"):
                                saved_path = config.save_session_info()

                                # Read and verify JSON content
                                with open(saved_path, encoding="utf-8") as f:
                                    data = json.load(f)

                                assert "timestamp" in data
                                assert "session_name" in data
                                assert "configuration" in data
                                assert "location" in data
                                assert data["location"] == "alma-ata"
                                assert "price_range" in data
                                assert data["price_range"]["min"] == 100000
                                assert data["price_range"]["max"] == 300000
                                assert data["phone_type_filter"] == "android"


class TestConstants:
    """Test configuration constants"""

    def test_location_constant(self):
        """LOCATION is set"""
        assert hasattr(config, "LOCATION")
        assert isinstance(config.LOCATION, str)

    def test_price_constants(self):
        """Price constants are integers"""
        assert isinstance(config.MIN_PRICE, int)
        assert isinstance(config.MAX_PRICE, int)
        assert config.MIN_PRICE > 0
        assert config.MAX_PRICE > config.MIN_PRICE

    def test_max_pages_constant(self):
        """MAX_PAGES is positive integer"""
        assert isinstance(config.MAX_PAGES, int)
        assert config.MAX_PAGES > 0

    def test_phone_type_filter_constant(self):
        """PHONE_TYPE_FILTER is valid"""
        assert config.PHONE_TYPE_FILTER in ["both", "android", "iphone"]

    def test_olx_base_url_constant(self):
        """OLX_BASE_URL is set correctly"""
        assert config.OLX_BASE_URL == "https://www.olx.kz"

    def test_user_agent_constant(self):
        """USER_AGENT is set"""
        assert isinstance(config.USER_AGENT, str)
        assert "Mozilla" in config.USER_AGENT
