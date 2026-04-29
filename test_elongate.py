import re

VOWELS = "aeiouyáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"

def elongate_word(word):
    # Find the last vowel in the word
    matches = list(re.finditer(f"[{VOWELS}]+", word, re.IGNORECASE))
    if not matches:
        return word
    
    last_match = matches[-1]
    vowel_group = last_match.group()
    
    # Duplicate the last character of the vowel group
    # or maybe just duplicate the whole vowel group?
    # Usually duplicating the last vowel char works best: 'người' -> 'ngườii'
    last_vowel_char = vowel_group[-1]
    
    # Actually, for 'người', replicating 'i' -> 'ngườii' works.
    # For 'tuyệt', 'ệ' is the last vowel, -> 'tuyệệt'
    # Wait, 'tuyệt' vowel group is 'uyệ'. Last is 'ệ'. 
    
    # Let's just duplicate the last character of the vowel group
    new_vowel_group = vowel_group + last_vowel_char
    
    # Replace in word
    return word[:last_match.start()] + new_vowel_group + word[last_match.end():]

def _apply_theanh28_style(text):
    # Find words before punctuation or end of string
    # We want to elongate the last word of a phrase/sentence
    # Punctuation: . , ! ? : ; …
    
    # We use regex to find a word followed by punctuation or end of string
    # \b([a-zA-Z_À-ỹ]+)\s*([.,?!:;…]+)
    
    def replace_func(match):
        word = match.group(1)
        punct = match.group(2)
        elongated = elongate_word(word)
        return elongated + punct

    # Match word at the end of text or before punctuation
    text = re.sub(r'([a-zA-Z_À-ỹ]+)\s*([.,?!:;…]+)', replace_func, text)
    return text

print(_apply_theanh28_style("Hôm nay là một ngày tuyệt vời, thời tiết rất đẹp."))
print(_apply_theanh28_style("Cảm ơn bạn nhé!"))
print(_apply_theanh28_style("Gió giật mạnh."))
