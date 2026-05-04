"""
Key Generator — Tạo License Key định dạng GWEN-XXXX-YYYY-ZZZZ.
"""

import secrets
import string


def generate_key(prefix: str = "GWEN") -> str:
    """Tạo license key ngẫu nhiên.
    
    Format: PREFIX-XXXX-YYYY-ZZZZ (16 ký tự sau prefix)
    Ký tự: A-Z + 0-9 (loại bỏ 0/O/I/1/L để tránh nhầm lẫn)
    
    Returns:
        Chuỗi key, ví dụ: 'GWEN-A3B7-K9M2-X4P8'
    """
    # Loại bỏ ký tự dễ nhầm: 0/O, 1/I/L
    chars = "".join(c for c in string.ascii_uppercase + string.digits 
                    if c not in "0OIL1")
    
    parts = []
    for _ in range(3):
        segment = "".join(secrets.choice(chars) for _ in range(4))
        parts.append(segment)
    
    return f"{prefix}-{'-'.join(parts)}"


if __name__ == "__main__":
    # Test: tạo 5 key mẫu
    for i in range(5):
        print(generate_key())
