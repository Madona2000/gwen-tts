import re

VOWELS = "aeiouyáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"

# Map vowels to their non-toned counterparts (but keeping the base hat like â, ă, ê, ô, ơ, ư)
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

def remove_tone(char):
    is_upper = char.isupper()
    c = char.lower()
    res = TONELESS_MAP.get(c, c)
    return res.upper() if is_upper else res

def elongate_word(word):
    matches = list(re.finditer(f"[{VOWELS}]+", word, re.IGNORECASE))
    if not matches:
        return word
    
    last_match = matches[-1]
    vowel_group = last_match.group()
    
    last_vowel_char = vowel_group[-1]
    toneless_vowel = remove_tone(last_vowel_char)
    
    new_vowel_group = vowel_group + toneless_vowel
    
    return word[:last_match.start()] + new_vowel_group + word[last_match.end():]

def _apply_theanh28_style(text):
    def replace_func(match):
        word = match.group(1)
        punct = match.group(2)
        elongated = elongate_word(word)
        return elongated + punct

    text = re.sub(r'([a-zA-Z_À-ỹ]+)\s*([.,?!:;…]+)', replace_func, text)
    return text

print(_apply_theanh28_style("Hôm nay là một ngày tuyệt vời, thời tiết rất đẹp."))
print(_apply_theanh28_style("Cảm ơn bạn nhé!"))
print(_apply_theanh28_style("Gió giật mạnh."))
print(_apply_theanh28_style("Đúng rồi đó."))
