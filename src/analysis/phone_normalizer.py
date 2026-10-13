#!/usr/bin/env python3
"""
Phone Name Normalizer
====================
Converts messy OLX titles into clean, standardized phone names.

Example:
  Input:  "Самсунг с 25 ультра s 25 ultra 300000"
  Output: "Samsung S25 Ultra (Самсунг с 25 ультра s 25 ultra 300000)"
"""

import re


class PhoneNormalizer:
    """Normalize phone titles to standard format"""

    @staticmethod
    def normalize_samsung_model(title: str) -> str | None:  # noqa: PLR0911
        """
        Extract and normalize Samsung model names

        Examples:
          "Samsung s25 ultra" -> "Samsung S25 Ultra"
          "Самсунг с 25 ультра" -> "Samsung S25 Ultra"
          "Galaxy S24 FE" -> "Samsung S24 FE"
        """
        title_lower = title.lower()

        # Z Fold/Flip series
        z_fold_match = re.search(r"z\s*фолд\s*(\d+)|z\s*fold\s*(\d+)", title_lower)
        if z_fold_match:
            num = z_fold_match.group(1) or z_fold_match.group(2)
            return f"Samsung Z Fold{num}"

        z_flip_match = re.search(r"z\s*флип\s*(\d+)|z\s*flip\s*(\d+)", title_lower)
        if z_flip_match:
            num = z_flip_match.group(1) or z_flip_match.group(2)
            return f"Samsung Z Flip{num}"

        # S series with FE
        s_fe_match = re.search(r"[sс]\s*(\d+)\s*fe", title_lower)
        if s_fe_match:
            return f"Samsung S{s_fe_match.group(1)} FE"

        # S series with Ultra
        s_ultra_match = re.search(r"[sс]\s*(\d+)\s*(ultra|ультра)", title_lower)
        if s_ultra_match:
            return f"Samsung S{s_ultra_match.group(1)} Ultra"

        # S series with Plus
        s_plus_match = re.search(r"[sс]\s*(\d+)\s*(plus|\+|плюс)", title_lower)
        if s_plus_match:
            return f"Samsung S{s_plus_match.group(1)} Plus"

        # S series base
        s_match = re.search(r"[sс]\s*(\d+)", title_lower)
        if s_match:
            return f"Samsung S{s_match.group(1)}"

        # A series
        a_match = re.search(r"[aа]\s*(\d+)", title_lower)
        if a_match:
            return f"Samsung A{a_match.group(1)}"

        return None

    @staticmethod
    def normalize_xiaomi_model(title: str) -> str | None:
        """
        Extract and normalize Xiaomi model names

        Examples:
          "Xiaomi 14 ultra" -> "Xiaomi 14 Ultra"
          "Mi 11" -> "Xiaomi 11"
          "Xiaomi 12s ultra" -> "Xiaomi 12S Ultra"
        """
        title_lower = title.lower()

        # Xiaomi with Ultra
        ultra_match = re.search(
            r"(?:xiaomi|сяоми|ксяоми|xioami|xiomi)\s*(\d+)s?\s*(ultra|ультра)", title_lower
        )
        if ultra_match:
            model = ultra_match.group(1)
            s_suffix = (
                "S"
                if "s" in ultra_match.group(0)
                and ultra_match.group(0).index("s")
                < ultra_match.group(0).index(ultra_match.group(2))
                else ""
            )
            return f"Xiaomi {model}{s_suffix} Ultra"

        # Xiaomi with T Pro
        t_pro_match = re.search(
            r"(?:xiaomi|сяоми|ксяоми|xioami|xiomi)\s*(\d+)\s*t\s*pro", title_lower
        )
        if t_pro_match:
            return f"Xiaomi {t_pro_match.group(1)}T Pro"

        # Xiaomi base model
        xiaomi_match = re.search(
            r"(?:xiaomi|сяоми|ксяоми|xioami|xiomi)\s*(\d+)\s*(t|lite|лайт|pro|про)?\b", title_lower
        )
        if xiaomi_match:
            suffix = {"t": "T", "lite": " Lite", "лайт": " Lite", "pro": " Pro", "про": " Pro"}
            return f"Xiaomi {xiaomi_match.group(1)}{suffix.get(xiaomi_match.group(2) or '', '')}"

        # Mi series
        mi_match = re.search(r"\bmi\s+(\d+)\s*(ultra|ультра)?", title_lower)
        if mi_match:
            ultra_suffix = " Ultra" if mi_match.group(2) else ""
            return f"Xiaomi {mi_match.group(1)}{ultra_suffix}"

        return None

    @staticmethod
    def normalize_redmi_model(title: str) -> str | None:
        """
        Extract and normalize Redmi model names

        Examples:
          "Redmi note 13 pro" -> "Redmi Note 13 Pro"
          "Редми ноте 13 про" -> "Redmi Note 13 Pro"
        """
        title_lower = title.lower()

        # Redmi Note with Pro
        note_pro_match = re.search(
            r"(?:redmi|редми|ридми)\s*(?:note|нот|ноте|нод)\s*(\d+)\s*(?:pro|про)", title_lower
        )
        if note_pro_match:
            return f"Redmi Note {note_pro_match.group(1)} Pro"

        # Redmi Note base
        note_match = re.search(
            r"(?:redmi|редми|ридми)\s*(?:note|нот|ноте|нод)\s*(\d+)", title_lower
        )
        if note_match:
            return f"Redmi Note {note_match.group(1)}"

        # Redmi with number only
        redmi_match = re.search(r"(?:redmi|редми|ридми)\s*(\d+)", title_lower)
        if redmi_match:
            return f"Redmi {redmi_match.group(1)}"

        return None

    @staticmethod
    def normalize_poco_model(title: str) -> str | None:
        """
        Extract and normalize POCO model names

        Examples:
          "Poco f6 pro" -> "POCO F6 Pro"
          "POCO X7 PRO" -> "POCO X7 Pro"
        """
        title_lower = title.lower()

        # POCO F series with Pro
        f_pro_match = re.search(r"poco\s*f\s*(\d+)\s*pro", title_lower)
        if f_pro_match:
            return f"POCO F{f_pro_match.group(1)} Pro"

        # POCO F series
        f_match = re.search(r"poco\s*f\s*(\d+)", title_lower)
        if f_match:
            return f"POCO F{f_match.group(1)}"

        # POCO X series with Pro
        x_pro_match = re.search(r"poco\s*x\s*(\d+)\s*pro", title_lower)
        if x_pro_match:
            return f"POCO X{x_pro_match.group(1)} Pro"

        # POCO X series
        x_match = re.search(r"poco\s*x\s*(\d+)", title_lower)
        if x_match:
            return f"POCO X{x_match.group(1)}"

        return None

    @staticmethod
    def normalize_oneplus_model(title: str) -> str | None:
        """
        Extract and normalize OnePlus model names

        Examples:
          "One plus 12" -> "OnePlus 12"
          "OnePlus 12R" -> "OnePlus 12R"
          "One Plus Nord 2" -> "OnePlus Nord 2"
        """
        title_lower = title.lower()

        # OnePlus with R suffix
        r_match = re.search(r"(?:oneplus|one\s*plus)\s*(\d+)\s*r", title_lower)
        if r_match:
            return f"OnePlus {r_match.group(1)}R"

        # OnePlus Nord
        nord_match = re.search(r"(?:oneplus|one\s*plus)\s*nord\s*(\d+)?", title_lower)
        if nord_match:
            num = f" {nord_match.group(1)}" if nord_match.group(1) else ""
            return f"OnePlus Nord{num}"

        # OnePlus base model
        oneplus_match = re.search(r"(?:oneplus|one\s*plus)\s*(\d+)", title_lower)
        if oneplus_match:
            return f"OnePlus {oneplus_match.group(1)}"

        return None

    @staticmethod
    def normalize_pixel_model(title: str) -> str | None:
        """
        Extract and normalize Google Pixel model names

        Examples:
          "Pixel 8 pro" -> "Google Pixel 8 Pro"
          "pixel 7a" -> "Google Pixel 7a"
        """
        title_lower = title.lower()

        # Pixel with Pro
        pro_match = re.search(r"pixel\s*(\d+)\s*pro", title_lower)
        if pro_match:
            return f"Google Pixel {pro_match.group(1)} Pro"

        # Pixel with 'a' suffix
        a_match = re.search(r"pixel\s*(\d+)\s*a", title_lower)
        if a_match:
            return f"Google Pixel {a_match.group(1)}a"

        # Pixel base model
        pixel_match = re.search(r"pixel\s*(\d+)", title_lower)
        if pixel_match:
            return f"Google Pixel {pixel_match.group(1)}"

        return None

    @staticmethod
    def normalize_iphone_model(title: str) -> str | None:
        """
        Extract and normalize iPhone model names

        Examples:
          "iPhone 15 pro max" -> "iPhone 15 Pro Max"
          "Айфон 14 про" -> "iPhone 14 Pro"
        """
        title_lower = title.lower()

        # iPhone with Pro Max
        pro_max_match = re.search(
            r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+|xs|xr|x|se)\s*(?:pro|про)\s*(?:max|макс|мах)",
            title_lower,
        )
        if pro_max_match:
            model = pro_max_match.group(1).upper()
            return f"iPhone {model} Pro Max"

        # iPhone with Pro
        pro_match = re.search(
            r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+|xs|xr|x|se)\s*(?:pro|про)",
            title_lower,
        )
        if pro_match:
            model = pro_match.group(1).upper()
            return f"iPhone {model} Pro"

        # iPhone with Plus
        plus_match = re.search(
            r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+)\s*(?:plus|\+|плюс)",
            title_lower,
        )
        if plus_match:
            return f"iPhone {plus_match.group(1)} Plus"

        if re.search(r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*xs\s*(?:max|макс|мах)", title_lower):
            return "iPhone XS Max"

        # iPhone base model
        iphone_match = re.search(
            r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+|xs|xr|x|se)",
            title_lower,
        )
        if iphone_match:
            model = iphone_match.group(1).upper()
            return f"iPhone {model}"

        return None

    @classmethod
    def normalize_phone_name(cls, title: str, detected_brand: str | None = None) -> str:
        """
        Normalize phone title to standard format

        Args:
            title: Original title from OLX
            detected_brand: Brand detected by brand detection system

        Returns:
            Normalized name in format: "Brand Model (Original Title)"
            If normalization fails, returns original title

        Examples:
            Input:  "Самсунг с 25 ультра s 25 ultra"
            Output: "Samsung S25 Ultra (Самсунг с 25 ультра s 25 ultra)"

            Input:  "Poco f6 pro 12/512"
            Output: "POCO F6 Pro (Poco f6 pro 12/512)"
        """
        # Try to normalize based on brand
        normalizers = {
            "samsung": cls.normalize_samsung_model,
            "xiaomi": cls.normalize_xiaomi_model,
            "redmi": cls.normalize_redmi_model,
            "poco": cls.normalize_poco_model,
            "oneplus": cls.normalize_oneplus_model,
            "pixel": cls.normalize_pixel_model,
            "iphone": cls.normalize_iphone_model,
        }

        # Try brand-specific normalization first
        if detected_brand and detected_brand.lower() in normalizers:
            normalized = normalizers[detected_brand.lower()](title)
            if normalized:
                return f"{normalized} ({title})"

        # Try all normalizers if brand not provided or not found
        for normalizer in normalizers.values():
            normalized = normalizer(title)
            if normalized:
                return f"{normalized} ({title})"

        # If no normalization succeeded, return original title
        return title


# Quick test
if __name__ == "__main__":
    test_cases = [
        ("Самсунг с 25 ультра s 25 ultra", "samsung"),
        ("Samsung s24 ultra 256gb", "samsung"),
        ("Poco f6 pro 12/512", "poco"),
        ("Xiaomi 14T Pro", "xiaomi"),
        ("Редми ноте 13 про", "redmi"),
        ("One plus 12R", "oneplus"),
        ("Pixel 8 pro", "pixel"),
        ("iPhone 15 pro max", "iphone"),
        ("Айфон 14 про макс", "iphone"),
    ]

    print("=" * 80)
    print("Phone Name Normalization Test")
    print("=" * 80)

    for title, brand in test_cases:
        normalized = PhoneNormalizer.normalize_phone_name(title, brand)
        print(f"\nOriginal:    {title}")
        print(f"Normalized:  {normalized}")
