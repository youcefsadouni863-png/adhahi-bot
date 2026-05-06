import os
import requests
import threading
import time
import sqlite3
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update

# 🔐 التوكن من environment
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
conn = sqlite3.connect("state.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS state (
    wilaya TEXT PRIMARY KEY,
    available INTEGER,
    last_report INTEGER
)
""")
conn.commit()


# ---------------- SAFE API CALL ----------------
def get_data():
    try:
        r = requests.get(
            API,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Referer": "https://adhahi.dz/"
            },
            timeout=10
        )

        if r.status_code != 200:
            print("HTTP Error:", r.status_code)
            return []

        if not r.text.strip():
            print("Empty response")
            return []

        return r.json()

    except Exception as e:
        print("API Error:", e)
        return []


# ---------------- TELEGRAM ----------------
def send(msg):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print("Telegram error:", e)


# ---------------- INIT DB ----------------
cur.execute("SELECT * FROM state WHERE wilaya=?", (WILAYA_CODE,))
row = cur.fetchone()

if row is None:
    cur.execute(
        "INSERT INTO state VALUES (?,?,?)",
        (WILAYA_CODE, 0, int(time.time()))
    )
    conn.commit()



# ---------------- LOOP ----------------
while True:
    try:
        data = get_data()

        for w in data:

            if w["wilayaCode"] != WILAYA_CODE:
                continue

            available = int(w["available"])
            name = w["wilayaNameFr"]

            cur.execute("SELECT available, last_report FROM state WHERE wilaya=?", (WILAYA_CODE,))
            old, last_report = cur.fetchone()

            now = int(time.time())

            # 🔥 1. إشعار عند فتح الحجز فقط
            if old == 0 and available == 1:
                send(f"🟢 الحجز أصبح متوفر الآن في: {name}")

            # 🔥 2. تقرير كل 10 دقائق (حتى لو مغلق)
            if now - last_report >= 250:
                status = "🟢 مفتوح" if available == 1 else "🔴 مغلق"

                time_str = datetime.now().strftime("%H:%M:%S")

                send(
                    f"📊 حالة الحجز (تحديث دوري)\n"
                    f"🏙 الولاية: {name}\n"
                    f"📌 الحالة: {status}\n"
                    f"⏰ الوقت: {time_str}"
                )

                last_report = now

            # تحديث الحالة
            cur.execute(
                "UPDATE state SET available=?, last_report=? WHERE wilaya=?",
                (available, last_report, WILAYA_CODE)
            )
            conn.commit()

        time.sleep(60)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(60)


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
