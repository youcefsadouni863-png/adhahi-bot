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
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ========== الإعدادات ==========
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL = 10 * 60  # 10 دقائق

API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"  # عدّله
WILAYA_CODE = "34"  # برج بوعريريج

# ================================

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"[{datetime.now()}] ✅ رسالة أُرسلت")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ خطأ في الإرسال: {e}")

def get_reservation_status():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        response = requests.get(API_URL, headers=headers, timeout=15, params={"wilaya": WILAYA_CODE})
        response.raise_for_status()
        data = response.json()

        status = data.get("status") or data.get("is_open") or data.get("reservation_open")
        return status
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
            f"🕐 الوقت: {datetime.now().strftime('%H:%M:%S - %Y/%m/%d')}"
        )
    else:
        return (
            f"📊 <b>تقرير دوري - حالة الحجز</b>\n"
            f"📍 الولاية: برج بوعريريج (34)\n"
            f"📌 الحالة: {status_ar}\n"
            f"🕐 الوقت: {datetime.now().strftime('%H:%M:%S - %Y/%m/%d')}"
        )

def main():
   

    last_status = None
    last_report_time = 0

    while True:
        current_status = get_reservation_status()

        if current_status is None:
            time.sleep(60)
            continue

        if last_status is not None and current_status != last_status:
            send_telegram_message(format_status_message(current_status, changed=True))
            last_report_time = time.time()

        elif time.time() - last_report_time >= CHECK_INTERVAL:
            send_telegram_message(format_status_message(current_status, changed=False))
            last_report_time = time.time()

        last_status = current_status
        time.sleep(60)

if __name__ == "__main__":
    main()
