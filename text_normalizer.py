#!/usr/bin/env python3
"""
Vietnamese Text Normalizer for Gwen-TTS

Converts numbers, symbols, abbreviations, and special characters
into spoken Vietnamese text before feeding into the TTS model.

This is critical because Gwen-TTS is fine-tuned from Qwen3-TTS (Chinese),
and its tokenizer tends to read raw digits in Chinese pronunciation.
"""

import re
import unicodedata


# ─────────────────────────────────────────────────────────────────────
# Number-to-Vietnamese-words conversion
# ─────────────────────────────────────────────────────────────────────

ONES = [
    "", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín",
]

def _read_two_digits(n, is_after_hundreds=False):
    """Read a two-digit number (0-99) in Vietnamese."""
    if n == 0:
        return ""
    tens = n // 10
    ones = n % 10

    result = []
    if tens == 0:
        if is_after_hundreds:
            result.append("lẻ")
        result.append(ONES[ones])
    elif tens == 1:
        result.append("mười")
        if ones == 5:
            result.append("lăm")
        elif ones == 1:
            # "mười một" (not "mười mốt" for 11 alone)
            result.append("một")
        elif ones != 0:
            result.append(ONES[ones])
    else:
        result.append(ONES[tens])
        result.append("mươi")
        if ones == 1:
            result.append("mốt")
        elif ones == 5:
            result.append("lăm")
        elif ones == 4:
            result.append("bốn")
        elif ones != 0:
            result.append(ONES[ones])

    return " ".join(result)


def _read_three_digits(n, is_after_higher=False):
    """Read a three-digit number (0-999) in Vietnamese."""
    if n == 0:
        return ""

    hundreds = n // 100
    remainder = n % 100

    parts = []
    if hundreds > 0:
        parts.append(f"{ONES[hundreds]} trăm")
        if remainder > 0:
            parts.append(_read_two_digits(remainder, is_after_hundreds=True))
    else:
        if is_after_higher:
            parts.append("không trăm")
        if remainder > 0:
            parts.append(_read_two_digits(remainder, is_after_hundreds=is_after_higher))

    return " ".join(parts)


# Vietnamese big-number units (groups of 3 digits from right)
_UNITS = ["", "nghìn", "triệu", "tỉ", "nghìn tỉ", "triệu tỉ"]


def number_to_vietnamese(n):
    """Convert an integer to Vietnamese words.

    Supports numbers up to trillions. Negative numbers are prefixed with 'âm'.

    Examples:
        0 -> "không"
        1 -> "một"
        15 -> "mười lăm"
        100 -> "một trăm"
        1000 -> "một nghìn"
        123456 -> "một trăm hai mươi ba nghìn bốn trăm năm mươi sáu"
    """
    if n < 0:
        return "âm " + number_to_vietnamese(-n)
    if n == 0:
        return "không"

    # Split into groups of 3 digits from right
    groups = []
    temp = n
    while temp > 0:
        groups.append(temp % 1000)
        temp //= 1000

    if len(groups) > len(_UNITS):
        # Fallback: read digit by digit for extremely large numbers
        return " ".join(ONES[int(d)] if d != '0' else "không" for d in str(n))

    parts = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        is_after_higher = (i < len(groups) - 1)
        text = _read_three_digits(g, is_after_higher=is_after_higher)
        if text:
            unit = _UNITS[i]
            parts.append(f"{text} {unit}".strip())

    return " ".join(parts) if parts else "không"


def _read_decimal(decimal_str):
    """Read decimal part digit-by-digit in Vietnamese."""
    digits = []
    for ch in decimal_str:
        if ch.isdigit():
            digits.append(ONES[int(ch)] if int(ch) > 0 else "không")
    return " ".join(digits)


# ─────────────────────────────────────────────────────────────────────
# Abbreviations and special terms
# ─────────────────────────────────────────────────────────────────────

ABBREVIATIONS = {
    "tp.hcm": "thành phố hồ chí minh",
    "tp hcm": "thành phố hồ chí minh",
    "tphcm": "thành phố hồ chí minh",
    "hn": "hà nội",
    "vn": "việt nam",
    "vnd": "đồng",
    "usd": "đô la mỹ",
    "eur": "ơ rô",
    "ceo": "xi i ô",
    "ai": "ây ai",
    "it": "ai ti",
    "gdp": "gi đi pi",
    "wto": "đáp liu ti ô",
    "apec": "ây pec",
    "asean": "a xê an",
    "unesco": "u nét xcô",
    "who": "đáp liu ết chờ ô",
    "covid": "cô vít",
    "iphone": "ai phôn",
    "facebook": "phây búc",
    "google": "gu gồ",
    "youtube": "du túp",
    "tiktok": "tích tóc",
}

# Measurement units (separate dict for number+unit matching)
UNIT_ABBR = {
    "km/h": "ki lô mét trên giờ",
    "m/s": "mét trên giây",
    "kg": "ki lô gam",
    "km": "ki lô mét",
    "cm": "xen ti mét",
    "mm": "mi li mét",
    "ml": "mi li lít",
    "mg": "mi li gam",
    "m2": "mét vuông",
    "m3": "mét khối",
    "km2": "ki lô mét vuông",
    "GHz": "gi ga héc",
    "MHz": "mê ga héc",
    "GB": "gi ga bai",
    "MB": "mê ga bai",
    "TB": "tê ra bai",
    "KB": "ki lô bai",
    "m": "mét",
}

# Units that can appear directly after a number
UNIT_MAP = {
    "đ": "đồng",
    "₫": "đồng",
    "$": "đô la",
    "€": "ơ-rô",
    "£": "pao",
    "¥": "yên",
    "%": "phần trăm",
    "°C": "độ xê",
    "°F": "độ ép",
    "°": "độ",
}

# Symbol replacements
SYMBOL_MAP = {
    "&": " và ",
    "+": " cộng ",
    "=": " bằng ",
    "@": " a-còng ",
    "#": " thăng ",
    "*": " nhân ",
    "/": " trên ",
    "~": " xấp xỉ ",
    "→": " dẫn đến ",
    "←": " từ ",
    "↑": " tăng ",
    "↓": " giảm ",
    "…": "...",
}


# ─────────────────────────────────────────────────────────────────────
# Main normalization pipeline
# ─────────────────────────────────────────────────────────────────────

def _normalize_abbreviations(text):
    """Replace known abbreviations with spoken forms."""
    # Sort by length (longest first) to avoid partial matches
    for abbr in sorted(ABBREVIATIONS.keys(), key=len, reverse=True):
        # Use word boundary for short abbreviations
        if len(abbr) <= 3:
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text = re.sub(pattern, ABBREVIATIONS[abbr], text)
        else:
            text = text.replace(abbr, ABBREVIATIONS[abbr])
    return text


def _normalize_date(text):
    """Convert date formats to Vietnamese spoken form.

    Supports:
        28/04/2026 -> "ngày hai mươi tám tháng tư năm hai nghìn không trăm hai mươi sáu"
        28-04-2026 -> same
        28/4 -> "ngày hai mươi tám tháng tư"
    """
    month_names = {
        1: "một", 2: "hai", 3: "ba", 4: "tư",
        5: "năm", 6: "sáu", 7: "bảy", 8: "tám",
        9: "chín", 10: "mười", 11: "mười một", 12: "mười hai",
    }

    def _replace_date_ymd(m):
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        month_word = month_names.get(month, number_to_vietnamese(month))
        return f"ngày {number_to_vietnamese(day)} tháng {month_word} năm {number_to_vietnamese(year)}"

    def _replace_date_dm(m):
        day = int(m.group(1))
        month = int(m.group(2))
        month_word = month_names.get(month, number_to_vietnamese(month))
        return f"ngày {number_to_vietnamese(day)} tháng {month_word}"

    # dd/mm/yyyy or dd-mm-yyyy
    text = re.sub(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b', _replace_date_ymd, text)
    # dd/mm (no year)
    text = re.sub(r'\b(\d{1,2})[/](\d{1,2})\b', _replace_date_dm, text)

    return text


def _normalize_time(text):
    """Convert time formats to Vietnamese.

    14:30 -> "mười bốn giờ ba mươi phút"
    8h30 -> "tám giờ ba mươi phút"
    """
    def _replace_time(m):
        hour = int(m.group(1))
        minute = int(m.group(2))
        parts = [number_to_vietnamese(hour), "giờ"]
        if minute > 0:
            parts.append(number_to_vietnamese(minute))
            parts.append("phút")
        return " ".join(parts)

    text = re.sub(r'\b(\d{1,2}):(\d{2})\b', _replace_time, text)
    text = re.sub(r'\b(\d{1,2})[hH](\d{2})\b', _replace_time, text)

    return text


def _normalize_phone_number(text):
    """Read phone numbers digit-by-digit.

    0909-123-456 -> "không chín không chín một hai ba bốn năm sáu"
    """
    def _replace_phone(m):
        digits = re.sub(r'[\-\.\s]', '', m.group(0))
        return " ".join(ONES[int(d)] if int(d) > 0 else "không" for d in digits)

    # Vietnamese phone patterns: 0xxx-xxx-xxxx or 0xxxxxxxxx
    text = re.sub(r'\b0\d{2,3}[\-\.\s]?\d{3}[\-\.\s]?\d{3,4}\b', _replace_phone, text)

    return text


def _normalize_currency(text):
    """Handle currency amounts.

    500.000đ -> "năm trăm nghìn đồng"
    1.500.000 VND -> "một triệu năm trăm nghìn đồng"
    $100 -> "một trăm đô la"
    """
    # Vietnamese format: dots as thousand separators (e.g. 1.500.000đ)
    def _replace_vnd(m):
        num_str = m.group(1).replace(".", "")
        currency = m.group(2)
        try:
            n = int(num_str)
            unit = UNIT_MAP.get(currency, ABBREVIATIONS.get(currency, currency))
            return f"{number_to_vietnamese(n)} {unit}"
        except ValueError:
            return m.group(0)

    # Number with dots + currency symbol/abbr
    text = re.sub(
        r'(\d[\d.]*)\s*(đ|₫|vnd|vnđ|usd|\$|€|£)\b',
        _replace_vnd, text, flags=re.IGNORECASE
    )
    # $ prefix
    text = re.sub(
        r'\$\s*(\d[\d.]*)',
        lambda m: f"{number_to_vietnamese(int(m.group(1).replace('.', '')))} đô la",
        text
    )

    return text


def _normalize_percentage(text):
    """Convert percentages.

    95% -> "chín mươi lăm phần trăm"
    """
    def _replace_pct(m):
        num_str = m.group(1)
        if ',' in num_str or '.' in num_str:
            # Decimal percentage
            sep = ',' if ',' in num_str else '.'
            parts = num_str.split(sep)
            integer_part = number_to_vietnamese(int(parts[0]))
            decimal_part = _read_decimal(parts[1])
            return f"{integer_part} phẩy {decimal_part} phần trăm"
        else:
            return f"{number_to_vietnamese(int(num_str))} phần trăm"

    text = re.sub(r'(\d[\d.,]*)\s*%', _replace_pct, text)
    return text


def _normalize_numbers_with_units(text):
    """Handle numbers followed by units.

    100km -> "một trăm ki-lô-mét"
    50kg -> "năm mươi ki-lô-gam"
    35°C -> "ba mươi lăm độ xê"
    """
    # Handle degree symbols first (°C, °F, °)
    def _replace_degree(m):
        num_str = m.group(1).replace(".", "")
        unit = m.group(2)
        try:
            n = int(num_str)
            unit_word = UNIT_MAP.get(unit, unit)
            return f"{number_to_vietnamese(n)} {unit_word}"
        except ValueError:
            return m.group(0)

    text = re.sub(r'(\d[\d.]*)\s*(°C|°F|°)', _replace_degree, text)

    # Handle metric/digital units
    # Sort by length (longest first) to match km/h before km
    sorted_units = sorted(UNIT_ABBR.keys(), key=len, reverse=True)
    unit_pattern = '|'.join(re.escape(u) for u in sorted_units)

    def _replace_num_unit(m):
        num_str = m.group(1)
        unit = m.group(2)
        # Handle decimal numbers with units (e.g. 3.5m)
        if ',' in num_str:
            parts = num_str.split(',')
            int_part = number_to_vietnamese(int(parts[0]))
            dec_part = _read_decimal(parts[1])
            num_word = f"{int_part} phẩy {dec_part}"
        elif '.' in num_str:
            dot_parts = num_str.split('.')
            # Check if it looks like a decimal (not thousand separator)
            if len(dot_parts) == 2 and len(dot_parts[1]) <= 2:
                int_part = number_to_vietnamese(int(dot_parts[0]))
                dec_part = _read_decimal(dot_parts[1])
                num_word = f"{int_part} phẩy {dec_part}"
            else:
                # Thousand separator
                clean = num_str.replace('.', '')
                num_word = number_to_vietnamese(int(clean))
        else:
            num_word = number_to_vietnamese(int(num_str))
        unit_word = UNIT_ABBR.get(unit, unit)
        return f"{num_word} {unit_word}"

    if unit_pattern:
        text = re.sub(
            rf'(\d[\d.]*)\s*({unit_pattern})\b',
            _replace_num_unit, text
        )
    return text


def _normalize_dashes(text):
    """Normalize various dash characters.

    Rules:
    - "Hà Nội - Sài Gòn" (spaced dash between words) -> comma/pause
    - "2024-2025" (range between numbers) -> "đến"
    - "COVID-19" (compound word) -> keep as hyphen (model handles it)
    - "1-2-3" (enumeration) -> spaces
    """
    # Protect compound words with hyphens (word-number or word-word)
    # e.g. COVID-19, F-16, Wi-Fi, etc.
    # We temporarily replace them with a placeholder
    protected = []
    def _protect_compound(m):
        protected.append(m.group(0))
        return f"__COMPOUND_{len(protected)-1}__"
    text = re.sub(r'[A-Za-zÀ-ỹ]+-\d+', _protect_compound, text)
    text = re.sub(r'[A-Za-zÀ-ỹ]+-[A-Za-zÀ-ỹ]+', _protect_compound, text)

    # Number range: 2024-2025, 100-200 (only for 4+ digit numbers to avoid "1-2-3")
    text = re.sub(r'(\d{2,})\s*[–—-]\s*(\d{2,})', r'\1 đến \2', text)

    # Spaced dashes between words (used as pause/separator)
    text = re.sub(r'\s+[–—]\s+', ', ', text)
    text = re.sub(r'\s+-\s+', ', ', text)

    # Restore protected compounds (remove the hyphen, join as space for TTS)
    for i, compound in enumerate(protected):
        # For TTS, replace hyphen with space so model doesn't choke
        spoken = compound.replace('-', ' ')
        text = text.replace(f"__COMPOUND_{i}__", spoken)

    return text


def _normalize_decimal_numbers(text):
    """Handle decimal numbers.

    3.14 -> "ba phẩy mười bốn"
    0,5 -> "không phẩy năm"

    Note: Must be called AFTER date, currency, and unit normalization
    to avoid false matches.
    """
    def _replace_decimal(m):
        integer_str = m.group(1)
        decimal_str = m.group(2)
        integer_part = number_to_vietnamese(int(integer_str))
        decimal_part = _read_decimal(decimal_str)
        return f"{integer_part} phẩy {decimal_part}"

    # Comma as decimal separator (Vietnamese standard): 3,14
    text = re.sub(r'\b(\d+),(\d+)\b', _replace_decimal, text)

    # Dot as decimal separator when NOT thousand-separator pattern
    # Only match if decimal part is 1-3 digits (not thousands like 1.000)
    def _maybe_decimal(m):
        integer_str = m.group(1)
        decimal_str = m.group(2)
        # If decimal part is exactly 3 digits and integer is 1-3 digits,
        # it's likely a thousand separator (e.g. 1.000, 10.000)
        if len(decimal_str) == 3 and len(integer_str) <= 3:
            # Check if there are more dot-groups (e.g. 1.000.000)
            return m.group(0)  # Leave for integer handler
        integer_part = number_to_vietnamese(int(integer_str))
        decimal_part = _read_decimal(decimal_str)
        return f"{integer_part} phẩy {decimal_part}"

    text = re.sub(r'\b(\d+)\.(\d{1,2})\b', _maybe_decimal, text)

    return text


def _normalize_plain_numbers(text):
    """Convert remaining standalone numbers to Vietnamese words.

    Handles thousand-separator dots: 1.000.000 -> "một triệu"
    """
    def _replace_number(m):
        num_str = m.group(0)
        # Handle Vietnamese thousand separator: 1.000.000
        if '.' in num_str:
            parts = num_str.split('.')
            # Verify it's a thousand-separator pattern (groups of 3 after first)
            if all(len(p) == 3 for p in parts[1:]):
                clean = num_str.replace(".", "")
                try:
                    return number_to_vietnamese(int(clean))
                except ValueError:
                    return num_str
            return num_str  # Not a clean thousand-separator pattern
        try:
            return number_to_vietnamese(int(num_str))
        except ValueError:
            return num_str

    # Match numbers with optional dots (thousand separators)
    text = re.sub(r'\b\d{1,3}(?:\.\d{3})+\b', _replace_number, text)
    # Match plain integers
    text = re.sub(r'\b\d+\b', _replace_number, text)

    return text


def _normalize_symbols(text):
    """Replace remaining symbols with spoken equivalents."""
    for sym, word in SYMBOL_MAP.items():
        text = text.replace(sym, word)
    return text


def _normalize_chat_abbreviations(text):
    """Fix common Vietnamese chat abbreviations."""
    replacements = {
        r'\be\b': 'em',
        r'\ba\b': 'anh',
        r'\bko\b': 'không',
        r'\bk\b': 'không',
        r'\bdc\b': 'được',
        r'\bđc\b': 'được',
        r'\bng\b': 'người',
        r'\bns\b': 'nói',
        r'\bbn\b': 'bạn',
        r'\bvk\b': 'vợ',
        r'\bck\b': 'chồng',
        r'\btks\b': 'cảm ơn',
        r'\bths\b': 'thạc sĩ',
        r'\bts\b': 'tiến sĩ',
        r'\bpgs\b': 'phó giáo sư',
        r'\bgs\b': 'giáo sư',
    }

    for pat, rep in replacements.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)

    return text


def _normalize_case(text):
    """Convert uppercase Vietnamese text to lowercase.

    The Gwen-TTS model (fine-tuned from Qwen3-TTS) handles lowercase
    Vietnamese much better than uppercase. Words like 'RÃNH' get
    mispronounced when capitalized, but 'rãnh' reads correctly.

    This preserves Vietnamese diacritics during case conversion.
    """
    return text.lower()


def _strip_chinese_characters(text):
    """Remove stray Chinese/CJK characters that shouldn't appear in Vietnamese.

    The Qwen3 base model sometimes bleeds Chinese characters into the output.
    Vietnamese uses Latin script with diacritics, so any CJK ideographs
    are unwanted artifacts.
    """
    # CJK Unified Ideographs: U+4E00 to U+9FFF
    # CJK Extension A: U+3400 to U+4DBF
    # CJK Compatibility Ideographs: U+F900 to U+FAFF
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+', '', text)
    return text


def _ensure_punctuation(text):
    """Add period at end if no sentence-ending punctuation."""
    text = text.strip()
    if text and text[-1] not in '.!?;:…':
        text += '.'
    return text


def _format_punctuation_and_pauses(text):
    """
    Chuẩn hóa dấu câu để tạo điểm neo ngữ điệu rõ ràng cho mô hình TTS.
    - Chuyển nhiều dấu chấm thành dấu chấm lửng (ellipsis)
    - Đảm bảo dấu câu đứng sát từ phía trước để tránh bị đọc thành âm độc lập gây vấp.
    - Đảm bảo có khoảng trắng sau dấu câu.
    """
    # 1. Chuyển ... thành …
    text = re.sub(r'\.{2,}', '…', text)
    
    # 2. Đảm bảo dấu câu đứng sát từ phía trước (bỏ khoảng trắng trước dấu câu)
    text = re.sub(r'\s+([.,?!:;…])', r'\1', text)

    # 3. Đảm bảo có khoảng trắng SAU dấu câu (nhưng không phải TRƯỚC dấu câu)
    # Tìm dấu câu mà ngay sau nó không phải là khoảng trắng hoặc kết thúc chuỗi
    text = re.sub(r'([.,?!:;…])(?=[^\s.,?!:;…])', r'\1 ', text)

    return text


def _cleanup_whitespace(text):
    """Normalize multiple spaces and whitespace."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


# ─────────────────────────────────────────────────────────────────────
# Compound word smoothing — đọc liền từ ghép và tên riêng
# ─────────────────────────────────────────────────────────────────────

# Tên riêng cần đọc liền (dùng dấu gạch nối để ép AI đọc thành 1 cụm)
# Key phải viết THƯỜNG vì pipeline đã lowercase text trước bước này
PROPER_NAMES_SMOOTH = {
    "donald trump": "đô-nan-trăm",
    "đô nan trăm": "đô-nan-trăm",
    "đô-nan trăm": "đô-nan-trăm",
    "i-ran": "y-ran",
    "iran": "y-ran",
    "bảo tín mạnh hải": "bảo-tín mạnh-hải",
    "bảo tín": "bảo-tín",
    "phú quý": "phú-quý",
    "ancarat việt nam": "ancarat việt-nam",
    "hồ chí minh": "hồ-chí-minh",
    "sài gòn": "sài-gòn",
    "đông bắc bộ": "đông-bắc-bộ",
    "tây bắc bộ": "tây-bắc-bộ",
    "nam bộ": "nam-bộ",
    "trung bộ": "trung-bộ",
    "đồng bằng sông cửu long": "đồng-bằng sông-cửu-long",
    "đồng bằng sông hồng": "đồng-bằng sông-hồng",
}

# Từ ghép tiếng Việt thường bị AI đọc ngắt quãng giữa các âm tiết
# Ghép lại thành 1 token để model đọc liền
COMPOUND_WORDS_SMOOTH = {
    # Tài chính / Kinh tế
    "niêm yết": "niêm-yết",
    "giao dịch": "giao-dịch",
    "biến động": "biến-động",
    "chứng khoán": "chứng-khoán",
    "lãi suất": "lãi-suất",
    "thị trường": "thị-trường",
    "tỷ giá": "tỷ-giá",
    "tài sản": "tài-sản",
    "tích lũy": "tích-lũy",
    "ngân hàng": "ngân-hàng",
    "trung ương": "trung-ương",
    "lạm phát": "lạm-phát",
    "doanh nghiệp": "doanh-nghiệp",
    "đồng loạt": "đồng-loạt",
    "chiến lược": "chiến-lược",
    # Thời tiết
    "mưa dông": "mưa-dông",
    "mưa rào": "mưa-rào",
    "gió giật": "gió-giật",
    "rải rác": "rải-rác",
    "cục bộ": "cục-bộ",
    "nắng nóng": "nắng-nóng",
    "không khí": "không-khí",
    "áp thấp": "áp-thấp",
    "nhiệt độ": "nhiệt-độ",
    # Chung
    "khả năng": "khả-năng",
    "chuyên gia": "chuyên-gia",
    "lịch sử": "lịch-sử",
    "xung đột": "xung-đột",
    "vật chất": "vật-chất",
    "chính thức": "chính-thức",
    "hiện tại": "hiện-tại",
    "quốc tế": "quốc-tế",
    "quan trọng": "quan-trọng",
    "phát triển": "phát-triển",
    "ảnh hưởng": "ảnh-hưởng",
    "tình hình": "tình-hình",
    "hoạt động": "hoạt-động",
    "chính sách": "chính-sách",
    "kinh tế": "kinh-tế",
    "xã hội": "xã-hội",
}


def _smooth_compound_words(text):
    """Ghép các từ ghép và tên riêng thành 1 token để AI đọc liền.

    Bước này chạy SAU khi text đã được lowercase, nên tất cả key
    trong dict đều viết thường.
    """
    # Bước 1: Tên riêng (ưu tiên tên dài trước để tránh match partial)
    for original, smoothed in sorted(
        PROPER_NAMES_SMOOTH.items(), key=lambda x: len(x[0]), reverse=True
    ):
        text = text.replace(original, smoothed)

    # Bước 2: Từ ghép
    for original, smoothed in COMPOUND_WORDS_SMOOTH.items():
        text = re.sub(re.escape(original), smoothed, text)

    return text


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

# Vietnamese warmup prefix — chèn trước text để model "khởi động" giọng.
# Phần audio warmup sẽ được trim ra sau khi generate (xem _trim_warmup_audio).
# Giúp từ đầu tiên được đọc rõ ràng, không bị nuốt/cắt.
VIETNAMESE_WARMUP_PREFIX = ". "
VIETNAMESE_WARMUP_ENABLED = True


def normalize_vietnamese(text, add_warmup=True, theanh28_style=False):
    """Full Vietnamese text normalization pipeline for TTS.

    Converts numbers, symbols, abbreviations, dates, times,
    currencies, and special characters into spoken Vietnamese text.

    This should be called BEFORE passing text to the Gwen-TTS model
    to avoid Chinese pronunciation of numbers and garbled symbols.

    Args:
        text: Raw input text
        add_warmup: If True, prepend a Vietnamese warmup prefix to
                    prevent Chinese bleed-through on the first word.
                    The audio for this prefix should be trimmed after
                    generation.
        theanh28_style: If True, elongates the final word of phrases/sentences
                        to match the 'Theanh28' dramatic reading style.

    Returns:
        Normalized text ready for TTS synthesis
    """
    if not text:
        return text

    # Step 0: Unicode normalization
    text = unicodedata.normalize('NFC', text)

    # Step 1: Remove stray Chinese/CJK characters early
    text = _strip_chinese_characters(text)

    # Step 2: Lowercase all text for clearer pronunciation
    # Vietnamese diacritics are preserved during lowercasing.
    # This fixes issues like "RÃNH" being mispronounced.
    text = _normalize_case(text)

    # Step 3: Abbreviations (before number processing)
    text = _normalize_abbreviations(text)

    # Step 4: Chat abbreviations
    text = _normalize_chat_abbreviations(text)

    # Step 5: Dates (before generic number processing)
    text = _normalize_date(text)

    # Step 6: Times
    text = _normalize_time(text)

    # Step 7: Phone numbers (before generic numbers)
    text = _normalize_phone_number(text)

    # Step 8: Currency amounts
    text = _normalize_currency(text)

    # Step 9: Percentages
    text = _normalize_percentage(text)

    # Step 10: Numbers with units (100km, 50kg)
    text = _normalize_numbers_with_units(text)

    # Step 11: Dashes
    text = _normalize_dashes(text)

    # Step 12: Decimal numbers
    text = _normalize_decimal_numbers(text)

    # Step 13: Plain numbers (last, catches remaining digits)
    text = _normalize_plain_numbers(text)

    # Step 14: Remaining symbols
    text = _normalize_symbols(text)

    # Step 15: Smooth compound words & proper names (đọc liền)
    text = _smooth_compound_words(text)

    # Step 16: Punctuation (đảm bảo cuối câu có dấu chấm)
    text = _ensure_punctuation(text)

    # Step 16.5: Format Punctuation for pauses (chuẩn hóa khoảng trắng quanh dấu câu)
    text = _format_punctuation_and_pauses(text)

    # Step 17: Clean whitespace
    text = _cleanup_whitespace(text)

    return text


# ─────────────────────────────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        "Hôm nay là ngày 28/04/2026",
        "Dân số Việt Nam khoảng 100.000.000 người",
        "Giá vàng hôm nay là 92.500.000đ/lượng",
        "Tốc độ gió đạt 120km/h",
        "Nhiệt độ hôm nay là 35°C",
        "GDP tăng 6,5% trong năm 2025",
        "Chuyến bay Hà Nội - TP.HCM lúc 14:30",
        "Gọi cho tôi số 0909-123-456",
        "iPhone 15 có giá $999",
        "Từ năm 2024-2025, AI phát triển mạnh",
        "100 tỉ đồng",
        "COVID-19 đã ảnh hưởng toàn cầu",
        "Diện tích 100m2, cao 3.5m",
        "1-2-3 bước đơn giản",
        # Compound word tests
        "Bảo Tín Mạnh Hải niêm yết vàng trên thị trường",
        "Nhiệt độ giảm, mưa dông rải rác, gió giật mạnh",
        "Ngân hàng trung ương điều chỉnh lãi suất",
    ]

    print("=" * 60)
    print("Vietnamese Text Normalizer - Test Results")
    print("=" * 60)
    for tc in test_cases:
        result = normalize_vietnamese(tc)
        result_theanh28 = normalize_vietnamese(tc, theanh28_style=True)
        print(f"\n  Input:  {tc}")
        print(f"  Output: {result}")
        print(f"  T28 Style: {result_theanh28}")
    print("\n" + "=" * 60)
