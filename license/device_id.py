"""
Device ID — Tạo fingerprint phần cứng duy nhất cho mỗi máy tính.

Fingerprint được tạo từ:
  - Hostname máy (platform.node)
  - MAC address (uuid.getnode)
  - Kiến trúc CPU (platform.machine)
  - OS (platform.system)

Kết quả: chuỗi 16 ký tự hex in hoa, ổn định qua các lần khởi động.
Chỉ thay đổi khi người dùng đổi phần cứng mạng hoặc đổi máy.
"""

import hashlib
import platform
import uuid


def get_device_id() -> str:
    """Tạo Device ID duy nhất dựa trên phần cứng máy.
    
    Returns:
        Chuỗi 16 ký tự hex in hoa, ví dụ: 'A1B2C3D4E5F6G7H8'
    """
    raw_parts = [
        platform.node(),           # Hostname
        str(uuid.getnode()),       # MAC address (integer)
        platform.machine(),        # CPU architecture (arm64, x86_64, ...)
        platform.system(),         # OS (Darwin, Windows, Linux)
    ]
    raw = "-".join(raw_parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def get_device_info() -> dict:
    """Trả về thông tin thiết bị để lưu lên Firebase."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "hostname": platform.node(),
        "machine": platform.machine(),
    }


if __name__ == "__main__":
    print(f"Device ID: {get_device_id()}")
    print(f"Device Info: {get_device_info()}")
