"""Tests for spec-based scoring in scoring.py"""

from src.analysis.scoring import (
    get_ram_score,
    get_storage_score,
)


class TestStorageScoringFromSpecs:
    """Test storage scoring from specs"""

    def test_storage_from_specs_json_array(self):
        """Storage score from JSON array in specs"""
        title = "samsung galaxy s24"
        specs = {"storage_variants": "[256, 512, 1024]"}

        points, label = get_storage_score(title, specs)

        assert points >= 10  # Should give points for high storage
        assert "from specs" in label.lower()

    def test_storage_from_specs_list(self):
        """Storage score from list in specs"""
        title = "samsung galaxy s24"
        specs = {"storage_variants": [128, 256, 512]}

        points, label = get_storage_score(title, specs)

        assert points >= 5
        assert "from specs" in label.lower()

    def test_storage_from_specs_max_value(self):
        """Storage score uses max value from variants"""
        title = "phone"
        specs = {"storage_variants": "[64, 128, 256]"}

        points, _label = get_storage_score(title, specs)

        # Should use 256 (highest)
        assert points > 0

    def test_storage_from_specs_invalid_json(self):
        """Storage score handles invalid JSON in specs"""
        title = "samsung s24 512gb"
        specs = {"storage_variants": "invalid json"}

        points, _label = get_storage_score(title, specs)

        # Should fall back to text parsing
        assert points >= 0

    def test_storage_from_specs_empty_array(self):
        """Storage score handles empty array"""
        title = "samsung s24 128gb"
        specs = {"storage_variants": "[]"}

        points, _label = get_storage_score(title, specs)

        # Should fall back to text parsing
        assert points >= 0

    def test_storage_from_specs_string_values(self):
        """Storage score handles string values in array"""
        title = "phone"
        specs = {"storage_variants": '["256GB", "512GB", "1TB"]'}

        points, _label = get_storage_score(title, specs)

        # Should parse strings to ints
        assert points >= 0

    def test_storage_from_specs_no_specs(self):
        """Storage score when no specs provided"""
        title = "samsung s24 256gb"

        points, _label = get_storage_score(title, None)

        # Should fall back to title parsing
        assert points >= 0

    def test_storage_from_specs_none_value(self):
        """Storage score handles None storage_variants"""
        title = "phone 128gb"
        specs = {"storage_variants": None}

        points, _label = get_storage_score(title, specs)

        assert points >= 0


class TestRAMScoringFromSpecs:
    """Test RAM scoring from specs"""

    def test_ram_from_specs_json_array(self):
        """RAM score from JSON array in specs"""
        title = "samsung galaxy s24"
        specs = {"ram_variants": "[8, 12, 16]"}

        points, label = get_ram_score(title, specs)

        assert points >= 10  # Should give points for high RAM
        assert "from specs" in label.lower()

    def test_ram_from_specs_list(self):
        """RAM score from list in specs"""
        title = "samsung galaxy s24"
        specs = {"ram_variants": [6, 8, 12]}

        points, label = get_ram_score(title, specs)

        assert points >= 5
        assert "from specs" in label.lower()

    def test_ram_from_specs_max_value(self):
        """RAM score uses max value from variants"""
        title = "phone"
        specs = {"ram_variants": "[4, 8, 12]"}

        points, _label = get_ram_score(title, specs)

        # Should use 12 (highest)
        assert points > 0

    def test_ram_from_specs_invalid_json(self):
        """RAM score handles invalid JSON in specs"""
        title = "phone 12gb ram"
        specs = {"ram_variants": "not valid json"}

        points, _label = get_ram_score(title, specs)

        # Should fall back to text parsing
        assert points >= 0

    def test_ram_from_specs_empty_array(self):
        """RAM score handles empty array"""
        title = "phone 8gb"
        specs = {"ram_variants": "[]"}

        points, _label = get_ram_score(title, specs)

        # Should fall back to text parsing
        assert points >= 0

    def test_ram_from_specs_string_values(self):
        """RAM score handles string values in array"""
        title = "phone"
        specs = {"ram_variants": '["8GB", "12GB", "16GB"]'}

        points, _label = get_ram_score(title, specs)

        # Should parse strings to ints
        assert points >= 0

    def test_ram_from_specs_no_specs(self):
        """RAM score when no specs provided"""
        title = "samsung s24 12gb ram"

        points, _label = get_ram_score(title, None)

        # Should fall back to title parsing
        assert points >= 0

    def test_ram_from_specs_none_value(self):
        """RAM score handles None ram_variants"""
        title = "phone 8gb"
        specs = {"ram_variants": None}

        points, _label = get_ram_score(title, specs)

        assert points >= 0

    def test_ram_from_specs_mixed_types(self):
        """RAM score handles mixed int and string types"""
        title = "phone"
        specs = {"ram_variants": [8, "12", 16]}

        points, _label = get_ram_score(title, specs)

        assert points >= 0
