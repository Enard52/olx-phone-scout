"""Shared test fixtures for all tests"""

import json

import pytest


@pytest.fixture
def sample_phone_listing():
    """Sample phone listing data"""
    return {
        "title": "Samsung Galaxy S24 Ultra 256GB",
        "price": 350000,
        "link": "https://www.olx.kz/d/obyavlenie/samsung-s24-ultra-ID123456.html",
        "status": "Новый",
        "location": "Almaty",
        "image_url": "https://example.com/phone.jpg",
        "detected_brand": "samsung",
        "phone_type": "android",
        "brand_confidence": 95,
        "scraped_at": "2025-01-14T12:00:00",
    }


@pytest.fixture
def sample_phone_listings():
    """Multiple phone listings"""
    return [
        {
            "title": "Samsung Galaxy S24 Ultra 256GB",
            "price": 350000,
            "link": "https://www.olx.kz/d/obyavlenie/samsung-s24-ultra-ID1.html",
            "status": "Новый",
            "detected_brand": "samsung",
            "phone_type": "android",
            "brand_confidence": 95,
        },
        {
            "title": "Xiaomi 14 Ultra 512GB",
            "price": 280000,
            "link": "https://www.olx.kz/d/obyavlenie/xiaomi-14-ultra-ID2.html",
            "status": "Новый",
            "detected_brand": "xiaomi",
            "phone_type": "android",
            "brand_confidence": 90,
        },
        {
            "title": "Google Pixel 9 Pro 128GB",
            "price": 320000,
            "link": "https://www.olx.kz/d/obyavlenie/pixel-9-pro-ID3.html",
            "status": "Б/у",
            "detected_brand": "google",
            "phone_type": "android",
            "brand_confidence": 88,
        },
    ]


@pytest.fixture
def sample_market_prices():
    """Sample market price data"""
    return {
        "samsung s24 ultra": {
            "initial": 677024,
            "launch_currency": "USD",
            "original_price": 1269,
            "year": 2024,
            "tier": "flagship-ultra",
        },
        "xiaomi 14 ultra": {"initial": 479625, "year": 2024, "tier": "flagship-ultra"},
        "pixel 9 pro": {"initial": 532800, "year": 2024, "tier": "flagship"},
    }


@pytest.fixture
def sample_phone_specs():
    """Sample phone specifications"""
    return {
        "ram": "12GB",
        "storage_variants": "[256, 512, 1024]",
        "processor": "Snapdragon 8 Gen 3",
        "camera": "200MP",
        "display": "6.8 inch AMOLED 120Hz",
        "battery": "5000mAh",
        "chipset": "Snapdragon 8 Gen 3",
        "screen_size": "6.8",
        "refresh_rate": "120Hz",
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure"""
    # Create session directory structure
    session_dir = tmp_path / "sessions" / "test_session"
    session_dir.mkdir(parents=True)

    # Create subdirectories
    (session_dir / "results").mkdir()
    (session_dir / "reports").mkdir()
    (session_dir / "logs").mkdir()
    (session_dir / "cache").mkdir()

    return tmp_path


@pytest.fixture
def temp_listings_file(temp_data_dir, sample_phone_listings):
    """Create temporary listings JSON file"""
    listings_file = temp_data_dir / "sessions" / "test_session" / "all_listings.json"
    data = {"phones": sample_phone_listings, "total": len(sample_phone_listings)}
    listings_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return listings_file


@pytest.fixture
def mock_olx_html():
    """Mock OLX HTML page with listings"""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div data-cy="l-card">
            <a href="/d/obyavlenie/samsung-s24-ultra-ID123.html"></a>
            <h6>Samsung Galaxy S24 Ultra 256GB</h6>
            <p data-testid="ad-price">350 000 ₸</p>
            <p data-testid="location-date">Almaty, Kazakhstan</p>
            <img src="https://example.com/samsung.jpg" />
        </div>
        <div data-cy="l-card">
            <a href="/d/obyavlenie/xiaomi-14-ultra-ID124.html"></a>
            <h6>Xiaomi 14 Ultra 512GB</h6>
            <p data-testid="ad-price">280 000 ₸</p>
            <p data-testid="location-date">Almaty, Kazakhstan</p>
            <img src="https://example.com/xiaomi.jpg" />
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_kimovil_response():
    """Mock KiMoVil API response"""
    return {
        "name": "Samsung Galaxy S24 Ultra",
        "brand": "Samsung",
        "ram": "12GB",
        "storage": "256GB",
        "processor": "Snapdragon 8 Gen 3",
        "camera": "200MP",
        "display": "6.8 inch AMOLED",
        "battery": "5000mAh",
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "This phone offers excellent value with flagship specs at a competitive price. The camera system is top-tier and battery life is exceptional."
                        }
                    ]
                },
                "finishReason": "STOP",
                "safetyRatings": [],
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 100,
            "candidatesTokenCount": 50,
            "totalTokenCount": 150,
        },
    }


@pytest.fixture
def mock_cloud_llm_response():
    """Mock Cloud LLM API response"""
    return {
        "choices": [
            {
                "message": {
                    "content": "Great value flagship phone with excellent camera and performance.",
                    "role": "assistant",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
