#!/bin/bash

# Lấy đường dẫn thư mục hiện tại của file .command
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "============================================="
echo "   Đang khởi động Gwen-TTS Application...   "
echo "============================================="
echo "Bảng điều khiển giao diện sẽ tự động bật lên."

# Chạy GUI bằng trình khởi chạy đã được cấu hình trong .venv
.venv/bin/python gwen_tts_gui.py

# Giữ cửa sổ terminal không đóng liền nếu có lỗi xảy ra
echo "Đã đóng ứng dụng Gwen-TTS."
