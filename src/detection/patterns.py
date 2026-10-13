#!/usr/bin/env python3
"""
Centralized Brand Detection Patterns
- Improved typo tolerance
- Better model detection (S25, A21s, etc.)
- Mixed Cyrillic/Latin support
- Handles standalone model numbers
"""

import re

# Enhanced brand patterns with better coverage
BRAND_PATTERNS = {
    "iphone": {
        "patterns": [
            # Standard patterns
            r"iphone",
            r"айфон",
            r"ayfon",
            r"aifon",
            r"iphon",
            r"айфонн",
            r"i\s*phone",
            r"і\s*phone",
            r"айфан",
            # New: Mixed Cyrillic/Latin
            r"aйфон",
            r"айфоn",
            r"iфон",
            # NEW: Common typos
            r"ipnone",  # "iPnone 13 pro max"
            r"aифон",  # Mixed case
            # New: "Apple" keyword (but check for model numbers)
            r"apple\s*(\d+|x|xr|xs|se|pro|max)",
            # NEW: Standalone patterns (careful - strict matching)
            r"\b(11|12|13|14|15|16)\s*(pro\s*max|pro|max|plus|\+)",  # Must have pro/max/plus
            r"\b(11|12|13|14|15)\s*про\s*(макс|мах)",  # Russian variant
        ],
        "type": "iphone",
        "score": 100,
    },
    "samsung": {
        "patterns": [
            # Standard patterns
            r"samsung",
            r"самсунг",
            r"самсунгг",
            r"samsyng",
            r"samsun",
            r"самсунгь",
            r"sаmsung",
            r"самсьнг",
            r"самсынг",
            # New: Common typos
            r"самсун\b",
            r"samsusng",
            r"самсуснг",
            # New: Standalone model patterns (S25, A21s, etc.)
            r"\bs\s*\d{1,2}\s*(ultra|plus|\+)?\b",  # S25, S21 ultra, etc.
            r"\ba\s*\d{1,2}s?\b",  # A21s, A32, A52, etc.
            r"\bа\s*\d{1,2}s?\b",  # Russian А53, А21s, etc.
            # NEW: Z Fold standalone patterns (found 4 times)
            r"z\s*fold\s*\d+",  # "z fold 4", "Z FOLD 5"
            r"z\s*фолд\s*\d+",  # "z фолд 4" (Cyrillic)
            r"z\s*flip\s*\d+",  # "z flip 5"
        ],
        "type": "android",
        "score": 90,
    },
    "galaxy": {
        "patterns": [
            r"galaxy",
            r"галакси",
            r"galaksi",
            r"galaxi",
            r"гелекси",
            r"галаксі",
            r"geleksi",
        ],
        "type": "android",
        "score": 85,
    },
    "xiaomi": {
        "patterns": [
            r"xiaomi",
            r"сяоми",
            r"ксиаоми",
            r"xiomi",
            r"xiaomy",
            r"сяомі",
            r"шаоми",
            r"ксяоми",
            # NEW: Very common typo (found 4 times)
            r"xioami",  # "Xioami 14 T pro"
            # NEW: Mi standalone pattern
            r"\bmi\s+\d+",  # "Mi 10 ultra", "Mi 11"
        ],
        "type": "android",
        "score": 80,
    },
    "redmi": {
        "patterns": [
            # Standard patterns
            r"redmi",
            r"редми",
            r"redmy",
            r"redmі",
            r"редмі",
            r"ridmi",
            r"редмии",
            r"реджми",
            # New: Common typos
            r"ридми",
            r"редмi",
            r"редмы",
            # New: "Note" typos
            r"re[dt]mi\s*(note|ноут|нот|нод)",  # Handle "нод" typo
        ],
        "type": "android",
        "score": 80,
    },
    "poco": {
        "patterns": [r"poco", r"поко", r"poko", r"pосо", r"покко", r"росо", r"пококо"],
        "type": "android",
        "score": 75,
    },
    "realme": {
        "patterns": [r"realme", r"реалми", r"реалме", r"realmi", r"realmе", r"риалми", r"риалме"],
        "type": "android",
        "score": 70,
    },
    "oppo": {
        "patterns": [r"oppo", r"оппо", r"опо", r"оппа", r"орро"],
        "type": "android",
        "score": 70,
    },
    "vivo": {"patterns": [r"vivo", r"виво", r"віво", r"vіvo"], "type": "android", "score": 70},
    "huawei": {
        "patterns": [r"huawei", r"хуавей", r"хуавэй", r"huavei", r"huavey", r"хуавеи", r"хаваей"],
        "type": "android",
        "score": 80,
    },
    "honor": {
        "patterns": [r"honor", r"хонор", r"honar", r"honоr", r"хоннор", r"хонар", r"онор"],
        "type": "android",
        "score": 70,
    },
    "google": {
        "patterns": [r"google", r"гугл", r"гугле", r"googl", r"gogle"],
        "type": "android",
        "score": 90,
    },
    "pixel": {
        "patterns": [r"pixel", r"пиксель", r"пиксел", r"piksel", r"pixl"],
        "type": "android",
        "score": 90,
    },
    "oneplus": {
        "patterns": [r"oneplus", r"ванплюс", r"ванплас", r"one\s*plus", r"1\+", r"онеплюс"],
        "type": "android",
        "score": 85,
    },
    "motorola": {
        "patterns": [r"motorola", r"моторола", r"moto", r"мото"],
        "type": "android",
        "score": 65,
    },
    "nokia": {"patterns": [r"nokia", r"нокиа", r"нокия", r"nokіa"], "type": "android", "score": 60},
    "zte": {"patterns": [r"zte", r"зте", r"зет", r"ztе"], "type": "android", "score": 60},
    "nubia": {"patterns": [r"nubia", r"нубия", r"нубиа", r"nubіa"], "type": "android", "score": 65},
    "tecno": {
        "patterns": [
            r"tecno",
            r"текно",
            r"техно",
            r"тэкно",
            r"tесno",
            r"tehno",
            # NEW: Common typo
            r"techno",  # "Techno Camon 30s"
        ],
        "type": "android",
        "score": 55,
    },
    "infinix": {
        "patterns": [r"infinix", r"инфиникс", r"інфінікс", r"infinіx"],
        "type": "android",
        "score": 55,
    },
    "nothing": {
        "patterns": [r"nothing\s*phone", r"натинг", r"нотинг"],
        "type": "android",
        "score": 85,
    },
    "asus": {
        "patterns": [r"asus", r"асус", r"асуc", r"asus\s*rog", r"rog\s*phone"],
        "type": "android",
        "score": 75,
    },
    "blackshark": {
        "patterns": [r"black\s*shark", r"блэк\s*шарк", r"blackshark"],
        "type": "android",
        "score": 70,
    },
    "sony": {"patterns": [r"sony", r"сони", r"xperia", r"ксперия"], "type": "android", "score": 70},
    "lg": {"patterns": [r"\blg\b", r"лг"], "type": "android", "score": 60},
    "meizu": {"patterns": [r"meizu", r"мейзу", r"мэйзу"], "type": "android", "score": 65},
    "wiko": {"patterns": [r"wiko", r"вико", r"віко"], "type": "android", "score": 50},
    "oukitel": {"patterns": [r"oukitel", r"оукител", r"оукітел"], "type": "android", "score": 50},
    "blackberry": {
        "patterns": [r"blackberry", r"блэкберри", r"блекбері"],
        "type": "android",
        "score": 60,
    },
    # NEW BRANDS (from unknown.json analysis)
    "iqoo": {
        "patterns": [
            r"iqoo",  # "iQOO z10 turbo"
            r"iqо",  # Mixed
            r"iqоо",  # Cyrillic o
        ],
        "type": "android",
        "score": 70,
    },
    "redmagic": {
        "patterns": [
            r"red\s*magic",  # "Red Magic 9 pro"
            r"redmagic",
            r"ред\s*мэджик",
        ],
        "type": "android",
        "score": 70,
    },
    "vertu": {
        "patterns": [
            r"vertu",  # "Vertu Constellation"
            r"верту",
            r"вэрту",
        ],
        "type": "android",  # Luxury Android
        "score": 50,  # Low priority
    },
    "hotwav": {
        "patterns": [
            r"hotwav",  # "Hotwav Hyper 7 Pro"
            r"хотвав",
        ],
        "type": "android",
        "score": 45,  # Budget brand
    },
    "thuraya": {
        "patterns": [
            r"thuraya",  # "Thuraya XT" satellite phone
            r"тураия",
        ],
        "type": "android",  # Specialty
        "score": 40,  # Very low priority
    },
}


# "Oppo Reno7 (обмен на iphone 13 pro)": the phone after "на"/"for" is what the seller WANTS.
# Keeps the exchange word and what's before it, so "Обмен iPhone 12 на что-то" stays an iPhone 12.
_EXCHANGE_WISH_RE = re.compile(
    r"((?:обмен|обменя|меня|поменя|exchange|swap|trade|айырбас|ауыстыр)\w*[^.!?\n]*?)"
    r"\s+(?:на|for)\s[^.!?\n]*",
    re.IGNORECASE,
)


def strip_exchange_wish(text: str) -> str:
    """Drop the "exchange for <other phone>" part of a listing title."""
    return _EXCHANGE_WISH_RE.sub(r"\1", text)


def detect_phone_brand(text):
    """
    Detect phone brand with fuzzy matching and typo tolerance
    Returns: (brand_name, phone_type, confidence_score)
    """
    text_lower = strip_exchange_wish(text).lower()
    text_lower = re.sub(r"\s+", " ", text_lower)  # Normalize spaces

    best_match = None
    best_score = 0

    for brand, info in BRAND_PATTERNS.items():
        for pattern in info["patterns"]:
            try:
                if re.search(pattern, text_lower):
                    score = info["score"]
                    if score > best_score:
                        best_score = score
                        best_match = (brand, info["type"], score)
            except re.error:
                # Skip invalid regex patterns
                continue

    return best_match if best_match else ("unknown", "unknown", 0)


def extract_model_info(text):
    """
    Extract specific model information from text
    Returns: dict with model details or None
    """
    text_lower = text.lower()

    # iPhone models
    iphone_match = re.search(
        r"(iphone|айфон|apple|aйфон)\s*(xr|xs\s*max|xs|x|se|\d+)\s*(pro\s*max|pro|max|plus|\+)?",
        text_lower,
    )
    if iphone_match:
        model_num = iphone_match.group(2).upper()
        variant = iphone_match.group(3) if iphone_match.group(3) else ""
        return {
            "brand": "iphone",
            "model": f"iPhone {model_num} {variant}".strip().replace("  ", " "),
            "type": "iphone",
        }

    # Samsung models
    samsung_match = re.search(
        r"(samsung|самсунг|самсун)?\s*([sa])\s*(\d{1,2})s?\s*(ultra|plus|\+)?", text_lower
    )
    if samsung_match:
        series = samsung_match.group(2).upper()
        model_num = samsung_match.group(3)
        variant = samsung_match.group(4) if samsung_match.group(4) else ""
        return {
            "brand": "samsung",
            "model": f"Samsung {series}{model_num} {variant}".strip(),
            "type": "android",
        }

    # Redmi Note models
    redmi_match = re.search(
        r"(redmi|редми|ридми)\s*(note|ноут|нот|нод)\s*(\d+)\s*(pro)?", text_lower
    )
    if redmi_match:
        model_num = redmi_match.group(3)
        variant = " Pro" if redmi_match.group(4) else ""
        return {"brand": "redmi", "model": f"Redmi Note {model_num}{variant}", "type": "android"}

    return None
