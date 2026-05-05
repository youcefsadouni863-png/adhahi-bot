import requests
import time
import threading
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

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
CHAT_ID = os.getenv("CHAT_ID")

API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"
WILAYA_CODE = "34"

CHECK_INTERVAL = 10 * 60  # 10 دقائق
SLEEP_TIME = 60  # كل دقيقة


# ========== TELEGRAM ==========
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)


# ========== API ==========
def get_status():
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        data = r.json()

        for w in data:
            if w.get("wilayaCode") == WILAYA_CODE:
                return bool(w.get("available"))

        return None

    except Exception as e:
        print("API error:", e)
        return None


# ========== FORMAT ==========
def format_msg(status, changed=False):
    s = "🟢 مفتوح" if status else "🔴 مغلق"

    if changed:
        return f"🚨 تغيّرت الحالة!\n📌 {s}\n🕐 {datetime.now().strftime('%H:%M:%S')}"
    else:
        return f"📊 الحالة الحالية:\n📌 {s}\n🕐 {datetime.now().strftime('%H:%M:%S')}"


# ========== MAIN ==========
def main():
    last_status = None
    last_report = 0

    while True:
        try:
            status = get_status()

            if status is None:
                time.sleep(SLEEP_TIME)
                continue

            # أول تشغيل → تقرير فقط
            if last_status is None:
                send(format_msg(status))
                last_report = time.time()

            # تغير الحالة → إشعار فوري
            elif status != last_status:
                send(format_msg(status, True))
                last_report = time.time()

            # تقرير كل 10 دقائق
            elif time.time() - last_report >= CHECK_INTERVAL:
                send(format_msg(status))
                last_report = time.time()

            last_status = status
            time.sleep(SLEEP_TIME)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
