import re
def _apply_theanh28_style(text):
    def replace_func(match):
        before_last_word = match.group(1)
        last_word = match.group(2)
        punct = match.group(3)
        if punct.strip() == '.':
            punct = '!'
        return f"{before_last_word}… {last_word}{punct}"

    text = re.sub(r'(.*?)\s+([a-zA-Z_À-ỹ]+)\s*([.,?!:;…]+)', replace_func, text)
    return text

print(_apply_theanh28_style("Căng cực, một thanh niên có hành động lạ, khiến mạng xã hội xôn xao."))
