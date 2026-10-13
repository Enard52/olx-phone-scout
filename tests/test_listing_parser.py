"""Tests for ListingParser"""

from bs4 import BeautifulSoup

from src.fetchers.listing_parser import ListingParser


class TestListingParser:
    """Test ListingParser methods"""

    def test_extract_description_data_cy(self):
        """_extract_description finds description with data-cy"""
        parser = ListingParser()
        html = '<div data-cy="ad_description">Great phone in excellent condition</div>'
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_description(soup)

        assert result == "Great phone in excellent condition"

    def test_extract_description_css_class(self):
        """_extract_description falls back to CSS class"""
        parser = ListingParser()
        html = '<div class="css-g5mtvm-Text">Phone description here</div>'
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_description(soup)

        assert result == "Phone description here"

    def test_extract_description_not_found(self):
        """_extract_description returns empty when not found"""
        parser = ListingParser()
        html = "<div>No description element</div>"
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_description(soup)

        assert result == ""

    def test_get_photo_src_with_src(self):
        """_get_photo_src extracts src attribute"""
        parser = ListingParser()
        html = '<img src="https://example.com/photo.jpg" />'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("img")

        result = parser._get_photo_src(elem)

        assert result == "https://example.com/photo.jpg"

    def test_get_photo_src_with_data_src(self):
        """_get_photo_src falls back to data-src"""
        parser = ListingParser()
        html = '<img data-src="https://example.com/lazy.jpg" />'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("img")

        result = parser._get_photo_src(elem)

        assert result == "https://example.com/lazy.jpg"

    def test_get_photo_src_non_http(self):
        """_get_photo_src rejects non-HTTP URLs"""
        parser = ListingParser()
        html = '<img src="/relative/path.jpg" />'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("img")

        result = parser._get_photo_src(elem)

        assert result is None

    def test_get_photo_src_no_src(self):
        """_get_photo_src returns None when no src"""
        parser = ListingParser()
        html = '<img alt="photo" />'
        soup = BeautifulSoup(html, "html.parser")
        elem = soup.find("img")

        result = parser._get_photo_src(elem)

        assert result is None

    def test_extract_photos_data_cy(self):
        """_extract_photos finds photos with data-cy"""
        parser = ListingParser()
        html = """
        <div>
            <img data-cy="photo-gallery-image" src="https://example.com/photo1.jpg" />
            <img data-cy="photo-gallery-image" src="https://example.com/photo2.jpg" />
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_photos(soup)

        assert len(result) == 2
        assert "https://example.com/photo1.jpg" in result
        assert "https://example.com/photo2.jpg" in result

    def test_extract_photos_css_class(self):
        """_extract_photos finds photos with CSS class"""
        parser = ListingParser()
        html = '<img class="css-1bmvjcs" src="https://example.com/photo.jpg" />'
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_photos(soup)

        assert len(result) == 1
        assert result[0] == "https://example.com/photo.jpg"

    def test_extract_photos_from_div(self):
        """_extract_photos finds photos inside divs"""
        parser = ListingParser()
        html = """
        <div data-cy="adPhotos-swiperSlide">
            <img src="https://example.com/slide.jpg" />
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_photos(soup)

        assert len(result) == 1
        assert result[0] == "https://example.com/slide.jpg"

    def test_extract_photos_deduplicates(self):
        """_extract_photos removes duplicates"""
        parser = ListingParser()
        html = """
        <div>
            <img data-cy="photo-gallery-image" src="https://example.com/photo.jpg" />
            <img data-cy="photo-gallery-image" src="https://example.com/photo.jpg" />
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_photos(soup)

        assert len(result) == 1

    def test_extract_photos_no_photos(self):
        """_extract_photos returns empty list when no photos"""
        parser = ListingParser()
        html = "<div>No photos here</div>"
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_photos(soup)

        assert result == []

    def test_find_key_value_elements_valid(self):
        """_find_key_value_elements finds key and value spans"""
        parser = ListingParser()
        html = "<div><span>RAM</span><span>8GB</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        param = soup.find("div")

        key_elem, val_elem = parser._find_key_value_elements(param)

        assert key_elem is not None
        assert val_elem is not None
        assert key_elem.get_text() == "RAM"
        assert val_elem.get_text() == "8GB"

    def test_find_key_value_elements_insufficient_spans(self):
        """_find_key_value_elements returns None when not enough spans"""
        parser = ListingParser()
        html = "<div><span>Only one span</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        param = soup.find("div")

        key_elem, val_elem = parser._find_key_value_elements(param)

        assert key_elem is None
        assert val_elem is None

    def test_extract_details_data_cy(self):
        """_extract_details extracts parameters with data-cy"""
        parser = ListingParser()
        html = """
        <div>
            <li data-cy="parameters-item"><span>RAM</span><span>12GB</span></li>
            <li data-cy="parameters-item"><span>Storage</span><span>256GB</span></li>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_details(soup)

        assert result == {"RAM": "12GB", "Storage": "256GB"}

    def test_extract_details_css_class(self):
        """_extract_details extracts parameters with CSS class"""
        parser = ListingParser()
        html = """
        <div>
            <div class="css-1m8pcey"><span>Processor</span><span>Snapdragon</span></div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_details(soup)

        assert result == {"Processor": "Snapdragon"}

    def test_extract_details_no_details(self):
        """_extract_details returns empty dict when no details"""
        parser = ListingParser()
        html = "<div>No parameters</div>"
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_details(soup)

        assert result == {}

    def test_extract_view_count_found(self):
        """_extract_view_count extracts view count"""
        parser = ListingParser()
        html = '<span data-cy="ad-views-count">1234 views</span>'
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_view_count(soup)

        assert result == 1234

    def test_extract_view_count_not_found(self):
        """_extract_view_count returns 0 when not found"""
        parser = ListingParser()
        html = "<div>No view count</div>"
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_view_count(soup)

        assert result == 0

    def test_extract_view_count_no_numbers(self):
        """_extract_view_count returns 0 when no numbers"""
        parser = ListingParser()
        html = '<span data-cy="ad-views-count">No views</span>'
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_view_count(soup)

        assert result == 0

    def test_extract_metadata_all_fields(self):
        """_extract_metadata extracts all metadata fields"""
        parser = ListingParser()
        html = """
        <div>
            <span data-cy="ad-views-count">500 views</span>
            <h4 data-cy="seller_name">John Doe</h4>
            <span data-cy="ad-posted-at">2025-01-14</span>
            <span>ID 12345</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_metadata(soup)

        assert result["views"] == 500
        assert result["seller_name"] == "John Doe"
        assert result["posted_date"] == "2025-01-14"
        assert "ID" in result["ad_id"]

    def test_extract_metadata_minimal(self):
        """_extract_metadata returns minimal metadata when fields missing"""
        parser = ListingParser()
        html = "<div>Minimal content</div>"
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_metadata(soup)

        assert result["views"] == 0
        assert "seller_name" not in result
        assert "posted_date" not in result

    def test_extract_metadata_partial(self):
        """_extract_metadata handles partial data"""
        parser = ListingParser()
        html = """
        <div>
            <h4 data-cy="seller_name">Seller Name</h4>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = parser._extract_metadata(soup)

        assert result["views"] == 0
        assert result["seller_name"] == "Seller Name"
        assert "posted_date" not in result
