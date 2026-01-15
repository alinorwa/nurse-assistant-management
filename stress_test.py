import asyncio
import websockets
import requests
import json
import time

# إعدادات الاختبار
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/auth/login/"
# ضع بيانات مستخدم حقيقي هنا
USERNAME = "555" 
PASSWORD = "123"

async def attack():
    # 1. تسجيل الدخول للحصول على الكوكيز (sessionid)
    session = requests.Session()
    # نحتاج CSRF Token أولاً
    client = session.get(LOGIN_URL)
    if 'csrftoken' in client.cookies:
        csrftoken = client.cookies['csrftoken']
    else:
        print("❌ فشل في جلب CSRF Token")
        return

    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'csrfmiddlewaretoken': csrftoken
    }
    
    # تنفيذ الدخول
    response = session.post(LOGIN_URL, data=login_data, headers={"Referer": LOGIN_URL})
    
    if response.url == f"{BASE_URL}/auth/login/":
        print("❌ فشل تسجيل الدخول (تأكد من اسم المستخدم وكلمة المرور)")
        return

    print("✅ تم تسجيل الدخول بنجاح.")
    
    # استخراج الكوكيز لاستخدامها في الويب سوكيت
    cookies = session.cookies.get_dict()
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    
    # 2. الاتصال بالويب سوكيت (نحتاج معرفة Session ID، سنفترض 1 للاختبار)
    # ملاحظة: في الواقع يجب جلب رقم الجلسة، لكن لنجرب على الجلسة رقم 1 أو 2
    CHAT_SESSION_ID = "1" 
    WS_URL = f"ws://127.0.0.1:8000/ws/chat/{CHAT_SESSION_ID}/"

    print(f"🚀 بدء الهجوم على: {WS_URL}")
    
    async with websockets.connect(WS_URL, additional_headers={'Cookie': cookie_str}) as websocket:
        print("✅ تم فتح قناة WebSocket.")
        
        # 3. إرسال 50 رسالة بسرعة فائقة
        start_time = time.time()
        
        for i in range(50):
            message = {"message": f"Stress Test Message {i}"}
            await websocket.send(json.dumps(message))
            print(f"📤 أرسلت: {i}", end="\r")
            
            # استقبال الرد فوراً لنرى هل تم الحظر أم لا
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                data = json.loads(response)
                
                if 'error' in data:
                    print(f"\n⛔ تم الحظر من السيرفر عند الرسالة {i}: {data['error']}")
                    break # توقف إذا تم الحظر (وهذا دليل نجاح الحماية)
                
            except asyncio.TimeoutError:
                pass # لا يوجد رد فوري، أكمل الإرسال

        end_time = time.time()
        print(f"\n⏱️ الزمن المستغرق: {end_time - start_time:.2f} ثانية")

if __name__ == "__main__":
    asyncio.run(attack())