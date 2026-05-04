"""
Firebase Configuration cho Gwen-TTS License System.

⚠️  QUAN TRỌNG: File này chứa thông tin kết nối Firebase.
    Ở Phase 4 (PyArmor), file này sẽ được mã hóa để bảo vệ credentials.

Hướng dẫn cấu hình:
1. Vào Firebase Console → Project Settings
2. Copy "databaseURL" từ Realtime Database
3. Copy "Web API Key" từ Project Settings → General
4. Điền vào 2 biến bên dưới
"""

# ============================================================
# CẤU HÌNH FIREBASE — BẠN CẦN ĐIỀN THÔNG TIN FIREBASE CỦA BẠN
# ============================================================

# URL của Firebase Realtime Database
# Ví dụ: "https://your-project-id-default-rtdb.firebaseio.com"
FIREBASE_DATABASE_URL = "https://gwen-tts-default-rtdb.asia-southeast1.firebasedatabase.app"

# Web API Key (từ Firebase Console → Project Settings → General)
# Ví dụ: "AIzaSyC..."
FIREBASE_API_KEY = ""

# ============================================================
# CẤU HÌNH ỨNG DỤNG
# ============================================================

# Tên ứng dụng (hiển thị trên giao diện)
APP_NAME = "Gwen-TTS"

# Link Telegram admin để người dùng liên hệ mua key
ADMIN_TELEGRAM = "https://t.me/colado3979"

# Thời gian offline tối đa (giây) — cho phép chạy offline sau lần check cuối
# Mặc định: 86400 = 24 giờ
OFFLINE_GRACE_PERIOD = 86400

# Key format prefix
KEY_PREFIX = "GWEN"
