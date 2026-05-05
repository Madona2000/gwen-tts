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


import subprocess

def get_stable_hardware_id() -> str:
    """Lấy ID phần cứng cố định thay vì dùng uuid.getnode() có thể bị random trên Mac."""
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], 
                stderr=subprocess.DEVNULL
            ).decode("utf-8")
            for line in result.split("\n"):
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2]
        elif system == "Windows":
            # Ưu tiên PowerShell (hoạt động trên mọi Windows 10/11)
            # wmic đã bị Microsoft deprecated và XÓA khỏi nhiều bản Windows 11
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            try:
                result = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID"],
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    timeout=10,
                ).decode("utf-8").strip()
                if result and len(result) > 8:
                    return result
            except Exception:
                pass
            # Fallback: Registry MachineGuid (cố định, không cần admin, nhanh)
            try:
                result = subprocess.check_output(
                    ["reg", "query",
                     r"HKLM\SOFTWARE\Microsoft\Cryptography",
                     "/v", "MachineGuid"],
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    timeout=5,
                ).decode("utf-8")
                for line in result.split("\n"):
                    if "MachineGuid" in line:
                        return line.split()[-1].strip()
            except Exception:
                pass
        elif system == "Linux":
            with open("/etc/machine-id", "r") as f:
                return f.read().strip()
    except Exception:
        pass
    
    # Fallback
    return str(uuid.getnode())

def get_device_id() -> str:
    """Tạo Device ID duy nhất dựa trên phần cứng máy.
    
    Returns:
        Chuỗi 16 ký tự hex in hoa, ví dụ: 'A1B2C3D4E5F6G7H8'
    """
    raw_parts = [
        platform.node(),              # Hostname
        get_stable_hardware_id(),     # UUID cố định
        platform.machine(),           # CPU architecture
        platform.system(),            # OS
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
