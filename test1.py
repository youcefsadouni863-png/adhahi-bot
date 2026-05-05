from flask import Flask
import requests
import os
from datetime import datetime

app = Flask(__name__)

# إحضار المتغيرات من إعدادات Vercel
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API = "https://adhahi.dz/api/v1/public/wilaya-quotas"
WILAYA_CODE = "34" 

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

@app.route('/api/cron', methods=['GET'])
def monitor():
    try:
        r = requests.get(API, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return "API Error", 500
        
        data = r.json()
        for w in data:
            if str(w["wilayaCode"]) == WILAYA_CODE:
                available = int(w["available"])
                name = w["wilayaNameFr"]
                status = "🟢 مفتوح" if available == 1 else "🔴 مغلق"
                time_str = datetime.now().strftime("%H:%M:%S")

                # إرسال التقرير الدوري
                msg = (f"📊 حالة الحجز في {name}\n"
                       f"📌 الحالة: {status}\n"
                       f"⏰ الوقت: {time_str}")
                
                send_telegram(msg)
                return "Report Sent", 200
        
        return "Wilaya Not Found", 404
    except Exception as e:
        return str(e), 500

@app.route('/')
def home():
    return "Bot is running..."