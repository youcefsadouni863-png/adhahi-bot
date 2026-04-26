import os
import threading
import time
import requests
import sqlite3
from flask import Flask

TOKEN = "8724903589:AAHxw8L_wXMuzOGZfdZmZRXnJfyQ6gLY7Bc"
CHAT_ID = "5757683406"

API = "https://adhahi.dz/api/v1/public/wilaya-quotas"
WILAYA_CODE = "34"  # برج

# -------- DB --------
conn = sqlite3.connect("state.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS state (
    wilaya TEXT PRIMARY KEY,
    available INTEGER
)
""")
conn.commit()

cur.execute("SELECT available FROM state WHERE wilaya=?", (WILAYA_CODE,))
row = cur.fetchone()
if row is None:
    cur.execute("INSERT INTO state VALUES (?,?)", (WILAYA_CODE, 0))
    conn.commit()

# -------- Telegram --------
def send(msg):
    try:
        print("SENDING:", msg)  # 👈 باش تشوفها في logs
        requests.get(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            params={
                "chat_id": CHAT_ID,
                "text": msg,
                "disable_notification": False
            },
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

# -------- API --------
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
        if r.status_code != 200 or not r.text.strip():
            print("Bad response:", r.status_code)
            return []
        return r.json()
    except Exception as e:
        print("API error:", e)
        return []

# -------- BOT LOOP --------
def run_bot():
    print("BOT LOOP STARTED ✅")
    while True:
        try:
            print("checking...")  # 👈 لازم تظهر في logs

            data = get_data()

            for w in data:
                if w["wilayaCode"] != WILAYA_CODE:
                    continue

                available = int(w["available"])
                name = w["wilayaNameFr"]

                cur.execute("SELECT available FROM state WHERE wilaya=?", (WILAYA_CODE,))
                old = cur.fetchone()[0]

                # إشعار عند الفتح فقط
                if old == 0 and available == 1:
                    send(f"🟢 الحجز أصبح متوفر الآن في: {name}")

                cur.execute("UPDATE state SET available=? WHERE wilaya=?", (available, WILAYA_CODE))
                conn.commit()

            time.sleep(15)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(10)

# -------- FLASK --------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# 🚀 تشغيل البوت في الخلفية
threading.Thread(target=run_bot, daemon=True).start()

# 🚀 تشغيل السيرفر (مهم لـ Render)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)