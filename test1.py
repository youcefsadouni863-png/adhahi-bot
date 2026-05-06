import os
import requests
import threading
import time
from flask import Flask, request
from telegram import Bot, Update

# 🔐 التوكن من environment
TOKEN = os.environ.get("TOKEN")

bot = Bot(token=TOKEN)
app = Flask(__name__)

API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"

# تخزين المستخدمين
users = {}

# الولايات
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
        res = requests.get(API_URL, timeout=10)
        data = res.json()

        for w in data.get("data", []):
            if w["code"] == wilaya_code:
                return w["status"]

    except Exception as e:
        print("API ERROR:", e)

    return None


# 🟢 مراقبة الحالة
def check_status(user_id):
    while users.get(user_id, {}).get("running", False):
        wilaya_code = users[user_id]["wilaya"]

        new_status = get_status(wilaya_code)
        old_status = users[user_id]["last_status"]

        if new_status and new_status != old_status:
            users[user_id]["last_status"] = new_status

            try:
                bot.send_message(
                    chat_id=user_id,
                    text=f"🔔 تغيرت الحالة:\n{new_status}"
                )
            except Exception as e:
                print("SEND ERROR:", e)

        time.sleep(600)  # 10 دقائق


# 🟢 Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)

        if update.message:
            user_id = update.message.chat_id
            text = update.message.text

            # /start
            if text == "/start":
                keyboard = "\n".join(wilayas.keys())
                bot.send_message(
                    chat_id=user_id,
                    text=f"اختر الولاية:\n{keyboard}"
                )

            # /stop
            elif text == "/stop":
                if user_id in users:
                    users[user_id]["running"] = False
                    bot.send_message(chat_id=user_id, text="تم الإيقاف ⛔")
                else:
                    bot.send_message(chat_id=user_id, text="البوت غير مفعل")

            # اختيار ولاية
            elif text in wilayas:
                users[user_id] = {
                    "wilaya": wilayas[text],
                    "last_status": None,
                    "running": True
                }

                bot.send_message(
                    chat_id=user_id,
                    text=f"تم اختيار {text} ✅"
                )

                threading.Thread(
                    target=check_status,
                    args=(user_id,),
                    daemon=True
                ).start()

            else:
                bot.send_message(chat_id=user_id, text="أمر غير معروف")

    except Exception as e:
        print("WEBHOOK ERROR:", e)

    return "ok"


# 🟢 route اختبار
@app.route("/")
def home():
    return "Bot is running ✅"


# 🟢 تشغيل
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
