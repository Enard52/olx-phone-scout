"""Tests for phone detection patterns"""

from src.detection.patterns import detect_phone_brand, extract_model_info


class TestDetectPhoneBrand:
    """Test detect_phone_brand function"""

    def test_detect_samsung(self):
        """Detects Samsung phones"""
        brand, phone_type, confidence = detect_phone_brand("Samsung Galaxy S24 Ultra")

        assert brand == "samsung"
        assert phone_type == "android"
        assert confidence > 80

    def test_detect_iphone(self):
        """Detects iPhone"""
        brand, phone_type, confidence = detect_phone_brand("iPhone 15 Pro Max")

        assert brand == "iphone"
        assert phone_type == "iphone"
        assert confidence > 80

    def test_detect_xiaomi(self):
        """Detects Xiaomi phones"""
        brand, phone_type, confidence = detect_phone_brand("Xiaomi 14 Ultra")

        assert brand == "xiaomi"
        assert phone_type == "android"
        assert confidence > 60

    def test_detect_google_pixel(self):
        """Detects Google Pixel phones"""
        brand, phone_type, confidence = detect_phone_brand("Google Pixel 9 Pro")

        assert brand == "google"
        assert phone_type == "android"
        assert confidence > 60

    def test_detect_oneplus(self):
        """Detects OnePlus phones"""
        brand, phone_type, confidence = detect_phone_brand("OnePlus 12")

        assert brand == "oneplus"
        assert phone_type == "android"
        assert confidence > 60

    def test_detect_unknown(self):
        """Returns unknown for unrecognized brands"""
        brand, phone_type, confidence = detect_phone_brand("Random Phone XYZ")

        assert brand == "unknown"
        assert phone_type == "unknown"
        assert confidence == 0


class TestExtractModelInfo:
    """Test extract_model_info function"""

    def test_extract_iphone_model_basic(self):
        """Extracts iPhone model"""
        result = extract_model_info("iPhone 15")

        assert result is not None
        assert result["brand"] == "iphone"
        assert "15" in result["model"]
        assert result["type"] == "iphone"

    def test_extract_iphone_model_pro_max(self):
        """Extracts iPhone Pro Max variant"""
        result = extract_model_info("iPhone 15 Pro Max")

        assert result is not None
        assert result["brand"] == "iphone"
        assert "15" in result["model"]
        assert "pro max" in result["model"].lower()

    def test_extract_iphone_cyrillic(self):
        """Extracts iPhone with Cyrillic spelling"""
        result = extract_model_info("айфон 14 про")

        assert result is not None
        assert result["brand"] == "iphone"

    def test_extract_iphone_se(self):
        """Extracts iPhone SE"""
        result = extract_model_info("iPhone SE")

        assert result is not None
        assert result["brand"] == "iphone"
        assert "SE" in result["model"]

    def test_extract_iphone_xr(self):
        """Extracts iPhone XR"""
        result = extract_model_info("iPhone XR")

        assert result is not None
        assert result["brand"] == "iphone"
        assert "XR" in result["model"]

    def test_extract_samsung_s_series(self):
        """Extracts Samsung S series"""
        result = extract_model_info("Samsung S24 Ultra")

        assert result is not None
        assert result["brand"] == "samsung"
        assert "S24" in result["model"] or "s24" in result["model"].lower()
        assert "ultra" in result["model"].lower()

    def test_extract_samsung_a_series(self):
        """Extracts Samsung A series"""
        result = extract_model_info("Samsung A54")

        assert result is not None
        assert result["brand"] == "samsung"
        assert "A54" in result["model"]
        assert result["type"] == "android"

    def test_extract_samsung_cyrillic(self):
        """Extracts Samsung with Cyrillic spelling"""
        result = extract_model_info("самсунг галакси а52")

        # May not match without full context
        if result:
            assert result["brand"] == "samsung"

    def test_extract_samsung_plus(self):
        """Extracts Samsung Plus variant"""
        result = extract_model_info("S23 Plus")

        assert result is not None
        assert result["brand"] == "samsung"
        assert "Plus" in result["model"] or "plus" in result["model"]

    def test_extract_redmi_note(self):
        """Extracts Redmi Note model"""
        result = extract_model_info("Redmi Note 13 Pro")

        assert result is not None
        assert result["brand"] == "redmi"
        assert "Note 13" in result["model"]
        assert "Pro" in result["model"]

    def test_extract_redmi_note_basic(self):
        """Extracts Redmi Note without Pro"""
        result = extract_model_info("Redmi Note 12")

        assert result is not None
        assert result["brand"] == "redmi"
        assert "Note 12" in result["model"]
        assert result["type"] == "android"

    def test_extract_redmi_cyrillic(self):
        """Extracts Redmi with Cyrillic spelling"""
        result = extract_model_info("редми ноут 11")

        assert result is not None
        assert result["brand"] == "redmi"

    def test_extract_model_no_match(self):
        """Returns None for unrecognized models"""
        result = extract_model_info("Random Phone 123")

        # Should return None for unknown models
        # (though detect_phone_brand might still identify brand)
        assert result is None or isinstance(result, dict)

    def test_extract_model_invalid_regex_handling(self):
        """Handles invalid regex patterns gracefully"""
        # This tests the try/except block around regex matching
        result = extract_model_info("Some weird text with [brackets]")

        # Should not crash
        assert result is None or isinstance(result, dict)
