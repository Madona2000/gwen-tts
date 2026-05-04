"""
License Checker — Xác thực License Key với Firebase Realtime Database.

Chức năng:
- Kiểm tra key tồn tại, còn hạn, status active
- Device binding: 1 key = 1 máy
- Cache key vào file local để hỗ trợ offline grace period
- REST API (không cần Firebase SDK nặng)
"""

import json
import os
import time
import base64
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .device_id import get_device_id, get_device_info
from .firebase_config import (
    FIREBASE_DATABASE_URL,
    OFFLINE_GRACE_PERIOD,
)


# ============================================================
# Local cache file — lưu key đã verify thành công
# ============================================================

def _get_cache_path() -> Path:
    """Trả về đường dẫn file cache license (~/.gwen_license)."""
    return Path.home() / ".gwen_license"


def _encode_cache(data: dict) -> str:
    """Mã hóa nhẹ (base64) dữ liệu cache để không bị đọc trực tiếp."""
    raw = json.dumps(data).encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def _decode_cache(encoded: str) -> dict:
    """Giải mã dữ liệu cache."""
    raw = base64.b64decode(encoded.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def save_license_cache(key: str, expires_at: str):
    """Lưu key đã verify thành công vào file local."""
    cache_data = {
        "key": key,
        "device_id": get_device_id(),
        "expires_at": expires_at,
        "last_verified": datetime.now(timezone.utc).isoformat(),
    }
    try:
        cache_path = _get_cache_path()
        cache_path.write_text(_encode_cache(cache_data), encoding="utf-8")
    except Exception as e:
        print(f"[License] Cảnh báo: Không thể lưu cache license: {e}")


def load_license_cache() -> dict | None:
    """Đọc key từ file cache local. Trả về None nếu không có."""
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None
    try:
        encoded = cache_path.read_text(encoding="utf-8").strip()
        data = _decode_cache(encoded)
        # Kiểm tra device_id khớp
        if data.get("device_id") != get_device_id():
            return None
        return data
    except Exception:
        return None


def clear_license_cache():
    """Xóa file cache license."""
    cache_path = _get_cache_path()
    if cache_path.exists():
        cache_path.unlink()


# ============================================================
# Firebase REST API
# ============================================================

def _firebase_get(path: str) -> dict | None:
    """GET dữ liệu từ Firebase Realtime Database qua REST API.
    
    Args:
        path: Đường dẫn trong database, ví dụ 'licenses/GWEN-XXXX-YYYY-ZZZZ'
    
    Returns:
        dict dữ liệu hoặc None nếu không tìm thấy
    """
    if not FIREBASE_DATABASE_URL:
        raise ConnectionError(
            "Chưa cấu hình Firebase Database URL.\n"
            "Vui lòng mở file license/firebase_config.py và điền thông tin."
        )
    
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/{path}.json"
    
    try:
        req = Request(url, method="GET")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except HTTPError as e:
        if e.code == 404:
            return None
        raise ConnectionError(f"Firebase HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        raise ConnectionError(f"Không thể kết nối Firebase: {e.reason}")


def _firebase_patch(path: str, data: dict):
    """PATCH (cập nhật) dữ liệu lên Firebase Realtime Database.
    
    Args:
        path: Đường dẫn trong database
        data: Dict dữ liệu cần cập nhật
    """
    if not FIREBASE_DATABASE_URL:
        raise ConnectionError("Chưa cấu hình Firebase Database URL.")
    
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/{path}.json"
    body = json.dumps(data).encode("utf-8")
    
    try:
        req = Request(url, data=body, method="PATCH")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        raise ConnectionError(f"Firebase PATCH Error {e.code}: {e.reason}")
    except URLError as e:
        raise ConnectionError(f"Không thể kết nối Firebase: {e.reason}")


# ============================================================
# License Verification Logic
# ============================================================

class LicenseResult:
    """Kết quả xác thực license."""
    
    def __init__(self, valid: bool, message: str, expires_at: str = None,
                 plan: str = None, key: str = None):
        self.valid = valid
        self.message = message
        self.expires_at = expires_at
        self.plan = plan
        self.key = key
    
    def __bool__(self):
        return self.valid
    
    def __repr__(self):
        return f"LicenseResult(valid={self.valid}, message='{self.message}')"


def verify_license(key: str) -> LicenseResult:
    """Xác thực license key với Firebase.
    
    Quy trình:
    1. Kiểm tra key tồn tại trong Firebase
    2. Kiểm tra status = "active"
    3. Kiểm tra chưa hết hạn
    4. Kiểm tra device binding (1 key = 1 máy)
    5. Nếu chưa bind → bind device hiện tại
    6. Cập nhật last_seen
    7. Lưu cache local
    
    Args:
        key: License key, ví dụ 'GWEN-ABCD-1234-WXYZ'
    
    Returns:
        LicenseResult với valid=True/False và message mô tả
    """
    key = key.strip().upper()
    device_id = get_device_id()
    
    try:
        # 1. Lấy dữ liệu license từ Firebase
        license_data = _firebase_get(f"licenses/{key}")
        
        if license_data is None:
            return LicenseResult(
                valid=False,
                message="❌ Key không tồn tại. Vui lòng kiểm tra lại hoặc liên hệ admin.",
                key=key,
            )
        
        # 2. Kiểm tra status
        status = license_data.get("status", "unknown")
        if status != "active":
            return LicenseResult(
                valid=False,
                message=f"❌ Key đã bị vô hiệu hóa (trạng thái: {status}).",
                key=key,
            )
        
        # 3. Kiểm tra hạn sử dụng
        expires_at = license_data.get("expires_at", "")
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if now > exp_dt:
                    return LicenseResult(
                        valid=False,
                        message=f"❌ Key đã hết hạn vào {exp_dt.strftime('%d/%m/%Y %H:%M')}.\n"
                                f"Vui lòng liên hệ admin để gia hạn.",
                        key=key,
                        expires_at=expires_at,
                    )
            except ValueError:
                pass  # Nếu parse lỗi → bỏ qua check hạn
        
        # 4. Kiểm tra device binding
        bound_device = license_data.get("device_id")
        
        if bound_device is None or bound_device == "":
            # Chưa bind → bind device hiện tại
            device_info = get_device_info()
            _firebase_patch(f"licenses/{key}", {
                "device_id": device_id,
                "activated_at": datetime.now(timezone.utc).isoformat(),
            })
            # Lưu thông tin device
            _firebase_patch(f"devices/{device_id}", {
                "license_key": key,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                **device_info,
            })
            print(f"[License] Đã kích hoạt key trên thiết bị này (Device: {device_id[:8]}...)")
        
        elif bound_device != device_id:
            # Đã bind trên máy khác
            return LicenseResult(
                valid=False,
                message="❌ Key này đã được kích hoạt trên một thiết bị khác.\n"
                        "Mỗi key chỉ dùng được trên 1 máy.\n"
                        "Liên hệ admin nếu bạn muốn chuyển thiết bị.",
                key=key,
                expires_at=expires_at,
            )
        
        else:
            # Device khớp → cập nhật last_seen
            _firebase_patch(f"devices/{device_id}", {
                "last_seen": datetime.now(timezone.utc).isoformat(),
            })
        
        # 5. Xác thực thành công
        plan = license_data.get("plan", "unknown")
        
        # Format thông tin hạn
        exp_display = ""
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                remaining = exp_dt - datetime.now(timezone.utc)
                days_left = remaining.days
                exp_display = f" (còn {days_left} ngày)"
            except ValueError:
                exp_display = ""
        
        # 6. Lưu cache
        save_license_cache(key, expires_at)
        
        return LicenseResult(
            valid=True,
            message=f"✅ Xác thực thành công! Gói: {plan}{exp_display}",
            expires_at=expires_at,
            plan=plan,
            key=key,
        )
        
    except ConnectionError as e:
        # Không có mạng → thử dùng cache offline
        return _try_offline_verification(key, str(e))


def _try_offline_verification(key: str, error_msg: str) -> LicenseResult:
    """Thử xác thực offline bằng cache local.
    
    Cho phép chạy offline trong OFFLINE_GRACE_PERIOD (mặc định 24h)
    kể từ lần online verify cuối cùng.
    """
    cache = load_license_cache()
    
    if cache is None:
        return LicenseResult(
            valid=False,
            message=f"❌ Không thể kết nối server:\n{error_msg}\n\n"
                    f"Vui lòng kiểm tra kết nối mạng và thử lại.",
            key=key,
        )
    
    # Kiểm tra key trong cache có khớp không
    if cache.get("key") != key.strip().upper():
        return LicenseResult(
            valid=False,
            message="❌ Key không khớp với key đã kích hoạt trên máy này.",
            key=key,
        )
    
    # Kiểm tra thời gian offline
    last_verified = cache.get("last_verified", "")
    if last_verified:
        try:
            last_dt = datetime.fromisoformat(last_verified)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            
            if elapsed > OFFLINE_GRACE_PERIOD:
                return LicenseResult(
                    valid=False,
                    message="❌ Đã vượt quá thời gian cho phép offline.\n"
                            "Vui lòng kết nối mạng để xác thực lại.",
                    key=key,
                )
            
            hours_left = int((OFFLINE_GRACE_PERIOD - elapsed) / 3600)
            return LicenseResult(
                valid=True,
                message=f"✅ Chế độ offline (còn {hours_left}h trước khi cần kết nối lại)",
                expires_at=cache.get("expires_at"),
                key=key,
            )
        except ValueError:
            pass
    
    # Kiểm tra hạn sử dụng từ cache
    expires_at = cache.get("expires_at", "")
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp_dt:
                return LicenseResult(
                    valid=False,
                    message="❌ Key đã hết hạn.",
                    key=key,
                    expires_at=expires_at,
                )
        except ValueError:
            pass
    
    return LicenseResult(
        valid=True,
        message="✅ Chế độ offline (cache xác thực)",
        expires_at=expires_at,
        key=key,
    )


def get_cached_key() -> str | None:
    """Lấy key đã lưu trong cache. Trả về None nếu chưa có."""
    cache = load_license_cache()
    if cache:
        return cache.get("key")
    return None
