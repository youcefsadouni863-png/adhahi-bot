import requests
import os
import time
import sqlite3
import threading
from datetime import datetime
from flask import Flask

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API = "https://adhahi.dz/api/v1/public/wilaya-quotas"
WILAYA_CODE = "50"

# ---------------- DB ----------------
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

# ---------------- TELEGRAM ----------------
def send(msg):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print("Telegram error:", e)

# ---------------- API ----------------
def get_data():
    try:
        r = requests.get(API, timeout=10)
        return r.json()
    except Exception as e:
        print("API Error:", e)
        return []

# ---------------- INIT ----------------
cur.execute("SELECT * FROM state WHERE wilaya=?", (WILAYA_CODE,))
row = cur.fetchone()

if row is None:
    cur.execute(
        "INSERT INTO state VALUES (?,?,?)",
        (WILAYA_CODE, 0, int(time.time()))
    )
    conn.commit()

# ---------------- BOT LOOP ----------------
def run_bot():
    send("🚀 البوت يعمل الآن")

    while True:
        try:
            print("checking...")

            data = get_data()

            for w in data:
                if w["wilayaCode"] != WILAYA_CODE:
                    continue

                available = int(w["available"])
                name = w["wilayaNameFr"]

                cur.execute("SELECT available, last_report FROM state WHERE wilaya=?", (WILAYA_CODE,))
                old, last_report = cur.fetchone()

                now = int(time.time())

                if old == 0 and available == 1:
                    send(f"🟢 الحجز أصبح متوفر الآن في: {name}")

                if now - last_report >= 250:
                    status = "🟢 مفتوح" if available else "🔴 مغلق"
                    send(f"📊 {name}: {status}")
                    last_report = now

                cur.execute(
                    "UPDATE state SET available=?, last_report=? WHERE wilaya=?",
                    (available, last_report, WILAYA_CODE)
                )
                conn.commit()

            time.sleep(15)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(15)

# ---------------- FLASK ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

# تشغيل البوت في الخلفية
threading.Thread(target=run_bot).start()

# تشغيل السيرفر (مهم)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
