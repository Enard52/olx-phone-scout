"""Shared parsing logic for OLX listing pages."""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.core import constants
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ListingParser:
    """Contains all methods for parsing details from a BeautifulSoup object of an OLX page."""

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract full description from listing page."""
        selectors: list[tuple[str, dict[str, Any]]] = [
            ("div", {"data-cy": "ad_description"}),
            ("div", {"class": "css-g5mtvm-Text"}),
            ("div", {"class": "descriptionContent"}),
            ("div", {"id": "textContent"}),
        ]
        for tag, attrs in selectors:
            if elem := soup.find(tag, attrs):
                return elem.get_text(strip=True, separator=" ")
        logger.warning("Description not found with any selector")
        return ""

    def _get_photo_src(self, elem: Tag) -> str | None:
        """Get photo source URL from an element."""
        if src := (elem.get("src") or elem.get("data-src")):  # noqa: SIM102
            if isinstance(src, str) and src.startswith("http"):
                return src
        return None

    def _extract_photos(self, soup: BeautifulSoup) -> list[str]:
        """Extract all photo URLs from listing page."""
        photos = set()
        selectors: list[tuple[str, dict[str, Any]]] = [
            ("img", {"data-cy": "photo-gallery-image"}),
            ("img", {"class": "css-1bmvjcs"}),
            ("div", {"data-cy": "adPhotos-swiperSlide"}),
        ]

        for tag, attrs in selectors:
            for elem in soup.find_all(tag, attrs):
                if tag == "img":
                    if src := self._get_photo_src(elem):
                        photos.add(src)
                elif tag == "div":  # noqa: SIM102
                    if img_tag := elem.find("img"):  # noqa: SIM102
                        if src := self._get_photo_src(img_tag):
                            photos.add(src)
        return list(photos)

    def _find_key_value_elements(self, param: Tag) -> tuple[Tag | None, Tag | None]:
        """Find key and value elements within a parameter element."""
        spans = param.find_all("span")
        if len(spans) >= constants.MIN_SPANS_FOR_PARAM:
            return spans[0], spans[1]
        return None, None

    def _extract_details(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract structured details (parameters) from listing."""
        details = {}
        param_selectors: list[tuple[str, dict[str, Any]]] = [
            ("li", {"data-cy": "parameters-item"}),
            ("div", {"class": "css-1m8pcey"}),
        ]
        for tag, attrs in param_selectors:
            for param in soup.find_all(tag, attrs):
                key_elem, val_elem = self._find_key_value_elements(param)
                if key_elem and val_elem:
                    key = key_elem.get_text(strip=True)
                    value = val_elem.get_text(strip=True)
                    details[key] = value
        return details

    def _extract_view_count(self, soup: BeautifulSoup) -> int:
        """Extract view count from listing page."""
        if (elem := soup.find("span", {"data-cy": "ad-views-count"})) and (
            numbers := re.findall(r"\d+", elem.get_text(strip=True))
        ):
            return int(numbers[0])
        return 0

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract metadata like view count, posting date, etc."""
        metadata: dict[str, Any] = {"views": self._extract_view_count(soup)}
        if seller_elem := soup.find("h4", {"data-cy": "seller_name"}):
            metadata["seller_name"] = seller_elem.get_text(strip=True)
        if date_elem := soup.find("span", {"data-cy": "ad-posted-at"}):
            metadata["posted_date"] = date_elem.get_text(strip=True)
        if ad_id_elem := soup.find("span", string=lambda x: x and "ID" in str(x)):
            metadata["ad_id"] = ad_id_elem.get_text(strip=True)
        return metadata
