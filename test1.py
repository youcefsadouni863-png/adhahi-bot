import requests
import time
import threading
import os
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ========== Web Server ==========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()

# ========== CONFIG ==========
TOKEN = os.getenv("TOKEN")
API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"
CHECK_INTERVAL = 10 * 60
SLEEP_TIME = 60

users = {}

# ========== API ==========
def get_all_wilayas():
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        return r.json()
    except:
        return []

def get_status(wilaya_code):
    data = get_all_wilayas()
    for w in data:
        if w.get("wilayaCode") == wilaya_code:
            return bool(w.get("available")), w.get("wilayaNameFr")
    return None, None

# ========== MONITOR ==========
async def monitor(chat_id, app):
    last_status = None
    last_report = 0

    while users.get(chat_id, {}).get("active"):
        wilaya_code = users[chat_id]["wilaya"]
        status, name = get_status(wilaya_code)

        if status is None:
            await asyncio.sleep(SLEEP_TIME)
            continue

        now = time.time()

        if last_status is None:
            await app.bot.send_message(
                chat_id,
                f"📊 <b>الحالة الحالية</b>\n"
                f"📍 {name}\n"
                f"{'🟢 مفتوح' if status else '🔴 مغلق'}\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}",
                parse_mode="HTML"
            )
            last_report = now

        elif status != last_status:
            await app.bot.send_message(
                chat_id,
                f"🚨 <b>تغيّرت الحالة!</b>\n"
                f"📍 {name}\n"
                f"{'🟢 مفتوح الآن' if status else '🔴 مغلق الآن'}\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}",
                parse_mode="HTML"
            )
            last_report = now

        elif now - last_report >= CHECK_INTERVAL:
            await app.bot.send_message(
                chat_id,
                f"📊 <b>تقرير دوري</b>\n"
                f"📍 {name}\n"
                f"{'🟢 مفتوح' if status else '🔴 مغلق'}\n"
                f"🕐 {datetime.now().strftime('%H:%M:%S')}",
                parse_mode="HTML"
            )
            last_report = now

        last_status = status
        await asyncio.sleep(SLEEP_TIME)

# ========== COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if users.get(chat_id, {}).get("active"):
        await update.message.reply_text("⚠️ البوت شغال بالفعل، أوقفه أولاً عبر /stop")
        return

    data = get_all_wilayas()

    if not data:
        await update.message.reply_text("❌ خطأ في جلب البيانات، حاول مرة أخرى")
        return

    keyboard = []
    for w in data:
        name = w.get("wilayaNameFr", "")
        code = w.get("wilayaCode", "")
        if name and code:
            keyboard.append([InlineKeyboardButton(name, callback_data=code)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📍 اختر الولاية:", reply_markup=reply_markup)


async def select_wilaya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    wilaya_code = query.data

    users[chat_id] = {
        "active": False,
        "wilaya": wilaya_code
    }

    await query.edit_message_text(
        f"✅ تم اختيار الولاية: {wilaya_code}\n\n"
        f"اضغط /run لبدء المراقبة"
    )


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in users:
        await update.message.reply_text("❗ اختر الولاية أولاً عبر /start")
        return

    if users[chat_id]["active"]:
        await update.message.reply_text("⚠️ البوت شغال بالفعل")
        return

    users[chat_id]["active"] = True
    await update.message.reply_text("🚀 بدأت المراقبة، سيتم إشعارك عند أي تغيير")

    context.application.create_task(monitor(chat_id, context.application))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in users:
        users[chat_id]["active"] = False

    await update.message.reply_text("⛔ تم إيقاف المراقبة")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in users:
        await update.message.reply_text("❗ اختر الولاية أولاً عبر /start")
        return

    wilaya_code = users[chat_id]["wilaya"]
    st, name = get_status(wilaya_code)

    if st is None:
        await update.message.reply_text("❌ خ
