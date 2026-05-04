"""
Telegram Bot Admin — Quản lý License Key cho Gwen-TTS (Hỗ trợ nút bấm)
"""

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ============================================================
# CẤU HÌNH — ĐIỀN THÔNG TIN CỦA BẠN
# ============================================================

TELEGRAM_BOT_TOKEN = "8753602646:AAHh2wWVxdhgPIhOgsNpQcXplyOfUlK34sw"
FIREBASE_DATABASE_URL = "https://gwen-tts-default-rtdb.asia-southeast1.firebasedatabase.app"
ADMIN_USER_IDS = []

PLANS = {
    "1month": timedelta(days=30),
    "3month": timedelta(days=90),
    "6month": timedelta(days=180),
    "1year": timedelta(days=365),
}

KEY_PREFIX = "GWEN"

from key_generator import generate_key

# ============================================================
# Firebase API
# ============================================================

def firebase_get(path: str):
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/{path}.json"
    req = Request(url, method="GET")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def firebase_put(path: str, data: dict):
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/{path}.json"
    body = json.dumps(data).encode("utf-8")
    req = Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def firebase_patch(path: str, data: dict):
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/{path}.json"
    body = json.dumps(data).encode("utf-8")
    req = Request(url, data=body, method="PATCH")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def firebase_delete(path: str):
    url = f"{FIREBASE_DATABASE_URL.rstrip('/')}/{path}.json"
    req = Request(url, method="DELETE")
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

# ============================================================
# UI Helpers
# ============================================================

def is_admin(user_id: int) -> bool:
    if not ADMIN_USER_IDS:
        return True
    return user_id in ADMIN_USER_IDS

def get_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🎁 Tạo Key 1 Tháng", callback_data="gen|1month"),
            InlineKeyboardButton("🎁 Tạo Key 3 Tháng", callback_data="gen|3month")
        ],
        [
            InlineKeyboardButton("🎁 Tạo Key 6 Tháng", callback_data="gen|6month"),
            InlineKeyboardButton("🎁 Tạo Key 1 Năm", callback_data="gen|1year")
        ],
        [
            InlineKeyboardButton("📋 Xem danh sách Key", callback_data="list_keys"),
            InlineKeyboardButton("📊 Thống kê", callback_data="stats")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_key_management_menu(key: str, status: str):
    keyboard = []
    
    if status == "active":
        keyboard.append([InlineKeyboardButton("❌ Thu hồi (Khóa) Key", callback_data=f"revoke|{key}")])
    elif status == "revoked":
        keyboard.append([InlineKeyboardButton("✅ Mở khóa Key", callback_data=f"unrevoke|{key}")])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Gia hạn +1 Tháng", callback_data=f"extend|{key}|1month"),
        InlineKeyboardButton("🔄 +3 Tháng", callback_data=f"extend|{key}|3month")
    ])
    keyboard.append([
        InlineKeyboardButton("🗑️ Xóa vĩnh viễn Key này", callback_data=f"delete|{key}")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Trở về Menu chính", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# Handlers
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bạn không có quyền.")
        return
    
    text = (
        "🔐 *Quản Lý License Gwen-TTS*\n\n"
        "Chào mừng bạn! Vui lòng chọn chức năng bên dưới, hoặc dùng lệnh:\n"
        "`/check <key>` để tra cứu và quản lý 1 key cụ thể."
    )
    await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Sử dụng: `/check GWEN-XXXX-YYYY-ZZZZ`", parse_mode="Markdown")
        return
    
    key = context.args[0].upper()
    await send_key_detail(update.message.reply_text, key)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    data = query.data
    
    try:
        if data == "main_menu":
            await query.edit_message_text(
                "🔐 *Quản Lý License Gwen-TTS*\n\nChọn chức năng bên dưới:",
                reply_markup=get_main_menu(),
                parse_mode="Markdown"
            )
            
        elif data.startswith("gen|"):
            plan = data.split("|")[1]
            key = generate_key(KEY_PREFIX)
            now = datetime.now(timezone.utc)
            expires = now + PLANS[plan]
            
            firebase_put(f"licenses/{key}", {
                "plan": plan,
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
                "status": "active",
                "buyer_name": "",
                "device_id": None,
                "max_devices": 1,
                "activated_at": None,
                "created_by": query.from_user.username or str(query.from_user.id),
            })
            
            msg = (
                f"✅ *Tạo Key Thành Công!*\n\n"
                f"🔑 `{key}`\n\n"
                f"📦 Gói: *{plan}* ({PLANS[plan].days} ngày)\n"
                f"📅 Hết hạn: {expires.strftime('%d/%m/%Y %H:%M UTC')}\n\n"
                f"_Copy đoạn key trên gửi cho khách hàng._"
            )
            # Giữ lại thông báo mới và thêm nút quay lại
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Menu chính", callback_data="main_menu"),
                InlineKeyboardButton("⚙️ Quản lý key này", callback_data=f"manage|{key}")
            ]])
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
            
        elif data == "list_keys":
            all_licenses = firebase_get("licenses")
            if not all_licenses:
                await query.edit_message_text("📭 Chưa có key nào.", reply_markup=get_main_menu())
                return
            
            lines = []
            for k, v in all_licenses.items():
                st = "🟢" if v.get("status") == "active" else "🔴"
                pl = v.get("plan", "?")
                lines.append(f"{st} `{k}` ({pl})")
            
            msg = "📋 *Danh sách Key:*\n\n" + "\n".join(lines) + "\n\n_Dùng lệnh_ `/check <key>` _để quản lý._"
            if len(msg) > 4000:
                msg = msg[:4000] + "..."
            
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Trở về", callback_data="main_menu")]]), parse_mode="Markdown")
            
        elif data == "stats":
            all_licenses = firebase_get("licenses") or {}
            active = sum(1 for v in all_licenses.values() if v.get("status") == "active")
            revoked = sum(1 for v in all_licenses.values() if v.get("status") != "active")
            
            msg = (
                f"📊 *Thống kê*\n\n"
                f"🔢 Tổng số key: {len(all_licenses)}\n"
                f"🟢 Đang hoạt động: {active}\n"
                f"🔴 Đã thu hồi: {revoked}"
            )
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Trở về", callback_data="main_menu")]]), parse_mode="Markdown")
            
        elif data.startswith("manage|"):
            key = data.split("|")[1]
            await send_key_detail(query.edit_message_text, key)
            
        elif data.startswith("revoke|"):
            key = data.split("|")[1]
            firebase_patch(f"licenses/{key}", {"status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()})
            await send_key_detail(query.edit_message_text, key)
            
        elif data.startswith("unrevoke|"):
            key = data.split("|")[1]
            firebase_patch(f"licenses/{key}", {"status": "active"})
            await send_key_detail(query.edit_message_text, key)
            
        elif data.startswith("extend|"):
            _, key, plan = data.split("|")
            info = firebase_get(f"licenses/{key}")
            if info:
                now = datetime.now(timezone.utc)
                old_exp = info.get("expires_at", "")
                base_date = now
                if old_exp:
                    try:
                        exp_dt = datetime.fromisoformat(old_exp.replace("Z", "+00:00"))
                        if exp_dt > now: base_date = exp_dt
                    except: pass
                new_exp = base_date + PLANS[plan]
                firebase_patch(f"licenses/{key}", {"expires_at": new_exp.isoformat(), "status": "active"})
            await send_key_detail(query.edit_message_text, key)
            
        elif data.startswith("delete|"):
            key = data.split("|")[1]
            firebase_delete(f"licenses/{key}")
            # Xóa thiết bị liên kết nếu có
            firebase_delete(f"devices/{key}")
            await query.edit_message_text(f"✅ Đã xóa vĩnh viễn key `{key}`.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Trở về", callback_data="main_menu")]]), parse_mode="Markdown")
            
    except Exception as e:
        await query.message.reply_text(f"❌ Lỗi: {e}")

async def send_key_detail(send_func, key: str):
    data = firebase_get(f"licenses/{key}")
    if not data:
        await send_func(f"❌ Không tìm thấy key `{key}`", parse_mode="Markdown", 
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Trở về", callback_data="main_menu")]]))
        return
    
    now = datetime.now(timezone.utc)
    exp = data.get("expires_at", "")
    status = data.get("status", "unknown")
    
    remaining = "N/A"
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            delta = exp_dt - now
            if delta.total_seconds() > 0:
                remaining = f"{delta.days} ngày"
            else:
                remaining = "⚠️ ĐÃ HẾT HẠN"
                if status == "active": status = "expired"
        except: pass
    
    st_icon = "🟢" if status == "active" else "🔴"
    msg = (
        f"🔍 *Chi tiết Key*\n\n"
        f"🔑 `{key}`\n"
        f"📦 Gói: {data.get('plan', 'N/A')}\n"
        f"🔄 Trạng thái: {st_icon} {status}\n"
        f"⏰ Hết hạn: {exp}\n"
        f"⏳ Còn lại: {remaining}\n"
        f"📱 Device ID: {data.get('device_id', 'Chưa kích hoạt')}\n"
    )
    
    # Nút bấm cho key này
    await send_func(msg, reply_markup=get_key_management_menu(key, status), parse_mode="Markdown")


# ============================================================
# Main
# ============================================================

def main():
    print("🤖 Gwen-TTS License Bot đang khởi động...")
    # Thêm timeout cao để tránh lỗi kết nối
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).get_updates_read_timeout(42.0).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("   Gửi /start trên Telegram để bắt đầu.")
    app.run_polling()

if __name__ == "__main__":
    main()
