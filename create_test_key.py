#!/usr/bin/env python3
"""
Script tạo nhanh License Key test — chạy trực tiếp trên terminal.

Sử dụng:
  python create_test_key.py               # Tạo key 1 tháng
  python create_test_key.py 3month        # Tạo key 3 tháng
  python create_test_key.py 6month buyer  # Tạo key 6 tháng cho 'buyer'

⚠️  YÊU CẦU: Đã điền FIREBASE_DATABASE_URL trong license/firebase_config.py
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request

# Thêm thư mục gốc vào path
sys.path.insert(0, ".")
from license.firebase_config import FIREBASE_DATABASE_URL
from telegram_bot.key_generator import generate_key

PLANS = {
    "1month": timedelta(days=30),
    "3month": timedelta(days=90),
    "6month": timedelta(days=180),
    "1year": timedelta(days=365),
}


def create_key(plan: str = "1month", buyer: str = "") -> str:
    if not FIREBASE_DATABASE_URL:
        print("❌ Lỗi: Chưa cấu hình FIREBASE_DATABASE_URL!")
        print("   Mở file license/firebase_config.py và điền Database URL.")
        sys.exit(1)
    
    if plan not in PLANS:
        print(f"❌ Plan không hợp lệ: {plan}")
        print(f"   Chọn: {', '.join(PLANS.keys())}")
        sys.exit(1)
    
    key = generate_key("GWEN")
    now = datetime.now(timezone.utc)
    expires = now + PLANS[plan]
    
    license_data = {
        "plan": plan,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "status": "active",
        "buyer_name": buyer,
        "device_id": None,
        "max_devices": 1,
        "activated_at": None,
        "created_by": "admin_script",
    }
    
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/licenses/{key}.json"
    body = json.dumps(license_data).encode("utf-8")
    req = Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urlopen(req, timeout=10) as resp:
            resp.read()
        
        print(f"\n✅ Key đã tạo thành công!\n")
        print(f"   🔑 Key:      {key}")
        print(f"   📦 Gói:      {plan} ({PLANS[plan].days} ngày)")
        print(f"   📅 Hết hạn:  {expires.strftime('%d/%m/%Y %H:%M UTC')}")
        if buyer:
            print(f"   👤 Buyer:    {buyer}")
        print(f"\n   Copy key trên và nhập vào ứng dụng Gwen-TTS.")
        return key
    except Exception as e:
        print(f"❌ Lỗi kết nối Firebase: {e}")
        sys.exit(1)


if __name__ == "__main__":
    plan = sys.argv[1] if len(sys.argv) > 1 else "1month"
    buyer = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    create_key(plan, buyer)
