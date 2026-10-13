"""
Comprehensive tests for src/infrastructure/cache.py

Tests all cache management functionality:
- Cache initialization and loading
- Setting and getting cached values
- Saving to disk (JSON persistence)
- Clearing cache
- Cache key generation (MD5 hashing)
- Container protocol (__len__, __contains__)

Target: 80%+ coverage for cache.py (53 statements)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.infrastructure.cache import CustomCache


class TestCacheInitialization:
    """Test cache initialization and loading"""

    def test_init_with_new_cache_file(self):
        """Initialize with non-existent cache file creates empty cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()

            cache = CustomCache(cache_file, logger)

            assert cache.cache == {}
            assert len(cache) == 0
            assert cache.cache_file == cache_file

    def test_init_loads_existing_cache(self):
        """Initialize with existing cache file loads data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()

            # Create cache file with data (old format for backward compatibility test)
            cache_data = {"key1": "value1", "key2": "value2"}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            cache = CustomCache(cache_file, logger)

            # Cache auto-migrates old format on get()
            assert cache.get("key1") == "value1"
            assert cache.get("key2") == "value2"
            assert len(cache) == 2
            logger.info.assert_called()

    def test_init_handles_corrupted_cache_file(self):
        """Initialize with corrupted cache file returns empty cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()

            # Write invalid JSON
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write("invalid json{")

            cache = CustomCache(cache_file, logger)

            assert cache.cache == {}
            logger.warning.assert_called_once()


class TestCacheOperations:
    """Test basic cache get/set/has operations"""

    def test_get_existing_key(self):
        """Get returns value for existing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.cache["test_key"] = "test_value"

            assert cache.get("test_key") == "test_value"

    def test_get_nonexistent_key(self):
        """Get returns None for nonexistent key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            assert cache.get("nonexistent") is None

    def test_set_adds_key_and_saves(self):
        """Set adds key, saves to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("new_key", "new_value")

            # Check via get() method (abstracted from internal format)
            assert cache.get("new_key") == "new_value"
            assert cache_file.exists()

            # Verify saved to disk
            with open(cache_file, encoding="utf-8") as f:
                disk_data = json.load(f)
            assert "new_key" in disk_data
            assert disk_data["new_key"] == "new_value"

    def test_set_overwrites_existing_key(self):
        """Set overwrites existing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("key", "old_value")
            cache.set("key", "new_value")

            assert cache.get("key") == "new_value"

    def test_has_returns_true_for_existing_key(self):
        """Has returns True for existing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.cache["test_key"] = "value"

            assert cache.has("test_key") is True

    def test_has_returns_false_for_nonexistent_key(self):
        """Has returns False for nonexistent key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            assert cache.has("nonexistent") is False


class TestCacheSaving:
    """Test cache save functionality"""

    def test_save_creates_parent_directory(self):
        """Save creates parent directory if not exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "subdir" / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("key", "value")

            assert cache_file.parent.exists()
            assert cache_file.exists()

    def test_save_persists_to_json(self):
        """Save writes correct JSON format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("key1", "value1")
            cache.set("key2", {"nested": "data"})

            # Verify via get() method
            assert cache.get("key1") == "value1"
            assert cache.get("key2") == {"nested": "data"}

            # Read and verify JSON
            with open(cache_file, encoding="utf-8") as f:
                disk_data = json.load(f)

            assert disk_data["key1"] == "value1"
            assert disk_data["key2"] == {"nested": "data"}

    def test_save_handles_unicode(self):
        """Save handles Unicode characters correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("key", "Тест 测试 🔥")

            # Verify via get() method
            assert cache.get("key") == "Тест 测试 🔥"

            # Read and verify
            with open(cache_file, encoding="utf-8") as f:
                disk_data = json.load(f)

            assert disk_data["key"] == "Тест 测试 🔥"


class TestCacheClearing:
    """Test cache clear functionality"""

    def test_clear_empties_cache_dict(self):
        """Clear empties the cache dictionary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("key1", "value1")
            cache.set("key2", "value2")

            cache.clear()

            assert cache.cache == {}
            assert len(cache) == 0

    def test_clear_deletes_cache_file(self):
        """Clear deletes the cache file from disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("key", "value")
            assert cache_file.exists()

            cache.clear()

            assert not cache_file.exists()
            logger.info.assert_called()

    def test_clear_when_file_doesnt_exist(self):
        """Clear handles non-existent cache file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            # File doesn't exist
            assert not cache_file.exists()

            cache.clear()  # Should not raise error

            assert cache.cache == {}


class TestPhoneCacheKey:
    """Test phone cache key generation"""

    def test_generate_key_from_url(self):
        """Generate cache key from URL (MD5 hash)"""
        phone_data = {
            "url": "https://olx.kz/listing/12345",
            "title": "Samsung S24",
            "price": 100000,
        }

        key = CustomCache.generate_phone_cache_key(phone_data)

        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
        # Same URL should produce same hash
        key2 = CustomCache.generate_phone_cache_key(phone_data)
        assert key == key2

    def test_generate_key_from_title_price(self):
        """Generate cache key from title+price when no URL"""
        phone_data = {
            "title": "Samsung S24 Ultra",
            "price": 150000,
        }

        key = CustomCache.generate_phone_cache_key(phone_data)

        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length

    def test_generate_key_same_title_price_same_hash(self):
        """Same title+price produces same hash"""
        phone1 = {"title": "Samsung S24", "price": 100000}
        phone2 = {"title": "Samsung S24", "price": 100000}

        key1 = CustomCache.generate_phone_cache_key(phone1)
        key2 = CustomCache.generate_phone_cache_key(phone2)

        assert key1 == key2

    def test_generate_key_different_data_different_hash(self):
        """Different data produces different hash"""
        phone1 = {"title": "Samsung S24", "price": 100000}
        phone2 = {"title": "Samsung S24", "price": 200000}

        key1 = CustomCache.generate_phone_cache_key(phone1)
        key2 = CustomCache.generate_phone_cache_key(phone2)

        assert key1 != key2

    def test_generate_key_url_takes_priority(self):
        """URL takes priority over title+price"""
        phone1 = {
            "url": "https://olx.kz/listing/1",
            "title": "Samsung S24",
            "price": 100000,
        }
        phone2 = {
            "url": "https://olx.kz/listing/2",
            "title": "Samsung S24",
            "price": 100000,
        }

        key1 = CustomCache.generate_phone_cache_key(phone1)
        key2 = CustomCache.generate_phone_cache_key(phone2)

        # Different URLs = different keys (even if title+price same)
        assert key1 != key2

    def test_generate_key_empty_data(self):
        """Handle empty phone data"""
        phone_data = {}

        key = CustomCache.generate_phone_cache_key(phone_data)

        assert isinstance(key, str)
        assert len(key) == 32  # Still produces valid MD5 hash


class TestContainerProtocol:
    """Test container protocol (__len__, __contains__)"""

    def test_len_returns_cache_size(self):
        """__len__ returns number of cached items"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            assert len(cache) == 0

            cache.set("key1", "value1")
            assert len(cache) == 1

            cache.set("key2", "value2")
            assert len(cache) == 2

    def test_contains_returns_true_for_existing_key(self):
        """'in' operator returns True for existing key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            cache.set("test_key", "value")

            assert "test_key" in cache
            assert "nonexistent" not in cache


class TestCacheEdgeCases:
    """Test edge cases and error handling"""

    def test_set_complex_data_types(self):
        """Cache handles complex JSON-serializable data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()
            cache = CustomCache(cache_file, logger)

            complex_data = {
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "string": "test",
                "number": 123,
                "boolean": True,
                "null": None,
            }

            cache.set("complex", complex_data)
            retrieved = cache.get("complex")

            assert retrieved == complex_data

    def test_cache_survives_reload(self):
        """Cache persists across CustomCache instances"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache.json"
            logger = MagicMock()

            # First instance
            cache1 = CustomCache(cache_file, logger)
            cache1.set("persistent", "value")

            # Second instance (reload)
            cache2 = CustomCache(cache_file, logger)

            assert cache2.get("persistent") == "value"
            assert len(cache2) == 1


class TestCacheErrorHandling:
    """Test error handling"""
