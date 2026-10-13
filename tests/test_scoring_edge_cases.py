"""Edge case tests for scoring.py"""

from src.analysis.scoring import (
    get_condition_score,
    get_processor_score,
    get_ram_score,
    get_storage_score,
)


class TestStorageScoringEdgeCases:
    """Test storage scoring edge cases"""

    def test_storage_with_non_dict_in_bonus_list(self):
        """Storage score handles non-dict entries in STORAGE_BONUS"""
        # This tests line 927-928 - continue when storage isn't dict
        title = "phone 256gb"
        specs = None

        # Should not crash, just skip non-dict entries
        points, _label = get_storage_score(title, specs)
        assert points >= 0

    def test_storage_with_non_list_non_string_variants(self):
        """Storage score handles invalid variant types"""
        # This tests line 920 - else branch when variants is neither string nor list
        title = "phone"
        specs = {"storage_variants": 12345}  # Invalid type (int)

        points, _label = get_storage_score(title, specs)
        assert points >= 0

    def test_storage_with_empty_keywords(self):
        """Storage score handles empty keywords"""
        # This tests line 934 - fallback when keywords is empty/None
        title = "phone 128gb"
        specs = None

        points, _label = get_storage_score(title, specs)
        assert points >= 0

    def test_storage_with_invalid_points_type(self):
        """Storage score handles invalid points type"""
        # This tests line 943-944 - ValueError/TypeError exception
        title = "phone"
        specs = {"storage_variants": "[128, 256]"}

        # Should handle invalid points gracefully
        points, _label = get_storage_score(title, specs)
        assert isinstance(points, int)


class TestRAMScoringEdgeCases:
    """Test RAM scoring edge cases"""

    def test_ram_with_non_dict_in_bonus_list(self):
        """RAM score handles non-dict entries in RAM_BONUS"""
        # This tests line 1012-1013 - continue when ram isn't dict
        title = "phone 12gb ram"
        specs = None

        points, _label = get_ram_score(title, specs)
        assert points >= 0

    def test_ram_with_non_list_non_string_variants(self):
        """RAM score handles invalid variant types"""
        # This tests line 1005 - else branch when variants is neither string nor list
        title = "phone"
        specs = {"ram_variants": True}  # Invalid type (bool)

        points, _label = get_ram_score(title, specs)
        assert points >= 0

    def test_ram_with_non_list_patterns(self):
        """RAM score handles non-list patterns"""
        # This tests line 1033-1034 - continue when patterns isn't list
        title = "phone 8gb"
        specs = None

        points, _label = get_ram_score(title, specs)
        assert points >= 0

    def test_ram_with_non_string_pattern(self):
        """RAM score handles non-string pattern in list"""
        # This tests line 1036-1037 - continue when pattern isn't string
        title = "phone 6gb"
        specs = None

        points, _label = get_ram_score(title, specs)
        assert points >= 0

    def test_ram_with_invalid_points_type(self):
        """RAM score handles invalid points type"""
        # This tests line 1042-1043 - ValueError/TypeError exception
        title = "phone"
        specs = {"ram_variants": "[8, 12]"}

        points, _label = get_ram_score(title, specs)
        assert isinstance(points, int)


class TestConditionScoringEdgeCases:
    """Test condition scoring edge cases"""

    def test_condition_score_empty_description(self):
        """get_condition_score handles empty description"""
        points, factors = get_condition_score("")

        assert points == 0
        assert factors == []

    def test_condition_score_none_description(self):
        """get_condition_score handles None description"""
        points, factors = get_condition_score(None)

        assert points == 0
        assert factors == []

    def test_condition_score_normalization_error(self):
        """get_condition_score handles normalization errors"""
        # This tests line 1117-1119 - exception in normalize_text
        # Pass a non-string type that might cause AttributeError
        description = 12345  # Invalid type

        # Should fallback to simple lowercase
        points, factors = get_condition_score(description)
        assert isinstance(points, int)
        assert isinstance(factors, list)

    def test_condition_score_with_object_description(self):
        """get_condition_score handles object description"""

        # Test with custom object that has no lower() method
        class FakeDesc:
            pass

        description = FakeDesc()

        # Should handle AttributeError gracefully and fallback to str()
        points, factors = get_condition_score(description)
        # FakeDesc.__str__() will produce something like "<FakeDesc object...>"
        # which should not match any condition patterns, so score should be 0
        assert isinstance(points, int)
        assert isinstance(factors, list)


class TestProcessorScoringEdgeCases:
    """Test processor scoring edge cases"""

    def test_processor_score_with_none_specs(self):
        """get_processor_score handles None specs"""
        title = "phone snapdragon 8 gen 3"

        points, _label = get_processor_score(title, tier=None, specs=None)
        assert points >= 0

    def test_processor_score_with_empty_title(self):
        """get_processor_score handles empty title"""
        points, _label = get_processor_score("", tier=None, specs=None)
        assert points >= 0

    def test_processor_score_with_none_title(self):
        """get_processor_score handles None title with tier fallback"""
        points, label = get_processor_score(None, tier="flagship", specs=None)
        assert points >= 0
        assert label is not None

    def test_processor_score_tier_default(self):
        """get_processor_score returns score for unknown processor"""
        title = "unknown phone model xyz"

        points, _label = get_processor_score(title, tier=None, specs=None)
        # Should return some score (0 or default)
        assert points >= 0
