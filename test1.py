import requests
import threading
import os
import time
from flask import Flask, request
from telegram import Bot, Update

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"

users = {}

wilayas = {
    "الجزائر": "16",
    "برج بوعريريج": "34",
    "سطيف": "19",
    "قسنطينة": "25",
    "وهران": "31"
}


# 🟢 جلب الحالة
def get_status(wilaya_code):
    try:
        res = requests.get(API_URL)
        data = res.json()

        for w in data["data"]:
            if w["code"] == wilaya_code:
                return w["status"]

    except:
        return None


# 🟢 التشييك كل 10 دقائق
def check_status(user_id):
    while users.get(user_id, {}).get("running", False):
        wilaya_code = users[user_id]["wilaya"]

        new_status = get_status(wilaya_code)
        old_status = users[user_id]["last_status"]

        if new_status != old_status:
            users[user_id]["last_status"] = new_status
            bot.send_message(chat_id=user_id, text=f"🔔 الحالة تغيرت: {new_status}")

        time.sleep(600)


# 🟢 استقبال رسائل Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)

    if update.message:
        user_id = update.message.chat_id
        text = update.message.text

        if text == "/start":
            keyboard = "\n".join(wilayas.keys())
            bot.send_message(chat_id=user_id, text=f"اختر الولاية:\n{keyboard}")

        elif text == "/stop":
            if user_id in users:
                users[user_id]["running"] = False
                bot.send_message(chat_id=user_id, text="تم الإيقاف ⛔")

        elif text in wilayas:
            users[user_id] = {
                "wilaya": wilayas[text],
                "last_status": None,
                "running": True
            }

            bot.send_message(chat_id=user_id, text=f"تم اختيار {text} ✅")

            threading.Thread(target=check_status, args=(user_id,)).start()

        else:
            bot.send_message(chat_id=user_id, text="أمر غير معروف")

    return "ok"


# 🟢 تشغيل السيرفر
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
