import re

VOWELS = "aeiouyáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
TONELESS_MAP = {
    'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ắ': 'ă', 'ằ': 'ă', 'ẳ': 'ă', 'ẵ': 'ă', 'ặ': 'ă',
    'ấ': 'â', 'ầ': 'â', 'ẩ': 'â', 'ẫ': 'â', 'ậ': 'â',
    'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ế': 'ê', 'ề': 'ê', 'ể': 'ê', 'ễ': 'ê', 'ệ': 'ê',
    'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ố': 'ô', 'ồ': 'ô', 'ổ': 'ô', 'ỗ': 'ô', 'ộ': 'ô',
    'ớ': 'ơ', 'ờ': 'ơ', 'ở': 'ơ', 'ỡ': 'ơ', 'ợ': 'ơ',
    'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ứ': 'ư', 'ừ': 'ư', 'ử': 'ư', 'ữ': 'ư', 'ự': 'ư',
    'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
}

def _remove_tone(char):
    is_upper = char.isupper()
    c = char.lower()
    res = TONELESS_MAP.get(c, c)
    return res.upper() if is_upper else res

def _elongate_word(word, repeat=2):
    matches = list(re.finditer(f"[{VOWELS}]+", word, re.IGNORECASE))
    if not matches:
        return word
    last_match = matches[-1]
    vowel_group = last_match.group()
    last_vowel_char = vowel_group[-1]
    toneless_vowel = _remove_tone(last_vowel_char)
    new_vowel_group = vowel_group + (toneless_vowel * repeat)
    return word[:last_match.start()] + new_vowel_group + word[last_match.end():]

def _apply_theanh28_style(text):
    def replace_func(match):
        word = match.group(1)
        punct = match.group(2)
        elongated = _elongate_word(word, repeat=2)
        if '.' in punct:
            punct = punct.replace('.', '…')
        return elongated + punct
    text = re.sub(r'([a-zA-Z_À-ỹ]+)\s*([.,?!:;…]+)', replace_func, text)
    return text

print(_apply_theanh28_style("Xin chào, hôm nay thời tiết rất đẹp."))
print(_apply_theanh28_style("Cộng đồng mạng bất ngờ trước thông tin này."))
print(_apply_theanh28_style("Điều đó thật tuyệt vời!"))
