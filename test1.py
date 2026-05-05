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

# تخزين حالة المستخدم
users = {}  
# users[chat_id] = {
#   "active": True/False,
#   "wilaya": "34"
# }

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
            await app.bot.send_message(chat_id, f"📊 {name}: {'🟢 مفتوح' if status else '🔴 مغلق'}")
            last_report = now

        elif status != last_status:
            await app.bot.send_message(chat_id, f"🚨 تغيّرت الحالة في {name}: {'🟢 مفتوح' if status else '🔴 مغلق'}")
            last_report = now

        elif now - last_report >= CHECK_INTERVAL:
            await app.bot.send_message(chat_id, f"📊 تحديث {name}: {'🟢 مفتوح' if status else '🔴 مغلق'}")
            last_report = now

        last_status = status
        await asyncio.sleep(SLEEP_TIME)

# ========== COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    data = get_all_wilayas()

    # نصنع أزرار لكل ولاية
    for w in data:
        name = w["wilayaNameFr"]
        code = w["wilayaCode"]
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

    await query.edit_message_text(f"✅ تم اختيار الولاية: {wilaya_code}\n\nاضغط /run لبدء المراقبة")


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in users:
        await update.message.reply_text("❗ اختر الولاية أولاً عبر /start")
        return

    if users[chat_id]["active"]:
        await update.message.reply_text("⚠️ البوت شغال بالفعل")
        return

    users[chat_id]["active"] = True

    await update.message.reply_text("🚀 بدأ المراقبة")

    context.application.create_task(monitor(chat_id, context.application))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in users:
        users[chat_id]["active"] = False

    await update.message.reply_text("⛔ تم إيقاف البوت")

# ========== MAIN ==========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(select_wilaya))
    app.add_handler(CommandHandler("run", run))
    app.add_handler(CommandHandler("stop", stop))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
