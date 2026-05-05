import requests
import time
import threading
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== Web Server وهمي لـ Render ==========
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

# ========== الإعدادات ==========
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"
WILAYA_CODE = "34"

CHECK_INTERVAL = 10 * 60  # 10 دقائق
SLEEP_TIME = 60  # كل دقيقة

# ================================


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"[{datetime.now()}] ✅ رسالة أُرسلت")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ خطأ في الإرسال: {e}")


def get_reservation_status():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        response = requests.get(API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        # 🔥 نبحث عن ولاية برج
        for w in data:
            if w.get("wilayaCode") == WILAYA_CODE:
                return bool(w.get("available"))

        return None

    except Exception as e:
        print(f"[{datetime.now()}] ❌ خطأ في جلب البيانات: {e}")
        return None


def format_status_message(status, changed=False):
    status_ar = "🟢 مفتوح" if status else "🔴 مغلق"

    if changed:
        return (
            f"🚨 <b>تغيّرت حالة الحجز!</b>\n"
            f"📍 الولاية: برج بوعريريج (34)\n"
            f"📌 الحالة الجديدة: {status_ar}\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S - %Y/%m/%d')}"
        )
    else:
        return (
            f"📊 <b>تقرير دوري</b>\n"
            f"📍 الولاية: برج بوعريريج (34)\n"
            f"📌 الحالة: {status_ar}\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S - %Y/%m/%d')}"
        )


def main():
    send_telegram_message("🚀 البوت يعمل الآن")

    last_status = None
    last_report_time = 0

    while True:
        try:
            print("checking...")

            current_status = get_reservation_status()

            if current_status is None:
                time.sleep(SLEEP_TIME)
                continue

            # 🔥 أول تشغيل
            if last_status is None:
                send_telegram_message(format_status_message(current_status))
                last_report_time = time.time()

            # 🔥 إذا تغيّرت الحالة
            elif current_status != last_status:
                send_telegram_message(format_status_message(current_status, changed=True))
                last_report_time = time.time()

            # 🔥 تقرير كل 10 دقائق
            elif time.time() - last_report_time >= CHECK_INTERVAL:
                send_telegram_message(format_status_message(current_status))
                last_report_time = time.time()

            last_status = current_status

            time.sleep(SLEEP_TIME)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
