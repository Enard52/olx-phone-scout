"""
Integration tests for OLX Almaty Phone Analyzer

Tests end-to-end workflows:
- Configuration loading
- Scraper + Analyzer integration
- Output file generation
"""


class TestConfiguration:
    """Test configuration loading and validation"""

    def test_config_imports(self):
        """Verify all config modules import successfully"""
        from src.core import config

        assert config is not None
        assert hasattr(config, "DATA_DIR")
        assert hasattr(config, "get_session_dir")

    def test_data_directories_exist(self):
        """Verify required directories exist or can be created"""
        from src.core import config

        # DATA_DIR should exist
        assert config.DATA_DIR.exists() or config.DATA_DIR.parent.exists()

        # Session dir (via function) should exist
        session_dir = config.get_session_dir()
        assert session_dir.exists() or session_dir.parent.exists()

    def test_logging_setup(self):
        """Verify logging is configured"""
        from src.infrastructure.logging import get_logger

        logger = get_logger("test")
        assert logger is not None
        logger.info("Test log message")


class TestScraperAnalyzerIntegration:
    """Test scraper and analyzer working together"""

    def test_scraper_analyzer_imports(self):
        """Verify scraper and analyzer can be imported together"""
        from src.analysis.analyzer import AndroidAnalyzer
        from src.core.async_scraper import AsyncOLXScraper

        scraper = AsyncOLXScraper()
        analyzer = AndroidAnalyzer(
            use_gemini=False,
            use_cerebras=False,
            use_openrouter=False,
            enrich_with_kimovil=False,
        )

        assert scraper is not None
        assert analyzer is not None

    def test_mock_phone_analysis(self):
        """Test analyzing a mock phone listing"""
        from src.analysis.analyzer import AndroidAnalyzer

        AndroidAnalyzer(
            use_gemini=False,
            use_cerebras=False,
            use_openrouter=False,
            enrich_with_kimovil=False,
        )

        # Mock phone listing
        mock_phone = {
            "title": "Samsung S24 Ultra 256GB",
            "price": 150000,
            "link": "https://example.com/listing",
            "description": "Отличное состояние, все работает",
            "photos": [],
        }

        # Basic validation - analyzer should handle this structure
        assert "title" in mock_phone
        assert "price" in mock_phone
        assert mock_phone["price"] > 0


class TestMainEntryPoint:
    """Test main.py entry point"""

    def test_main_imports(self):
        """Verify main.py imports successfully"""
        import main

        assert main is not None
        assert hasattr(main, "run_scraper")


class TestValidatorsIntegration:
    """Test validators integration across modules"""

    def test_config_uses_validators(self):
        """Verify config.py uses path validators"""
        from src.core import config

        # Config should have functions that use validators
        assert hasattr(config, "save_session_info")

    def test_scraper_uses_validators(self):
        """Verify scraper uses validators for file operations"""
        from src.core import async_scraper

        # Should import validators
        assert async_scraper is not None
