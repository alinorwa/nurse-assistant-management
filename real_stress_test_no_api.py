import requests
import threading
import time
import re
import asyncio
import websockets
import json

# الإعدادات
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/auth/login/"
CHAT_URL = f"{BASE_URL}/chat/" # الرابط الذي يفتح صفحة HTML للشات
UPLOAD_URL = f"{BASE_URL}/chat/upload/" # View الرفع التقليدي

# إعدادات الضغط
NUM_USERS = 20         # عدد المستخدمين
NUM_IMAGE_SENDERS = 5  # عدد من يرسلون صوراً (لتوفير تكلفة Azure)

def bot_task(user_id):
    session = requests.Session()
    username = f"stress_user_{user_id}"
    password = "123"

    try:
        # ---------------------------------------------------------
        # 1. محاكاة المتصفح: زيارة صفحة الدخول لجلب الكوكيز
        # ---------------------------------------------------------
        login_page = session.get(LOGIN_URL)
        if 'csrftoken' not in session.cookies:
            print(f"❌ Bot {user_id}: No CSRF Token")
            return
        
        csrftoken = session.cookies['csrftoken']

        # ---------------------------------------------------------
        # 2. تسجيل الدخول (POST Form Data)
        # ---------------------------------------------------------
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrftoken
        }
        # مهم: Django يتطلب Referer في طلبات الدخول
        headers = {'Referer': LOGIN_URL}
        
        response = session.post(LOGIN_URL, data=login_data, headers=headers)
        
        # التأكد من النجاح (عادة يعيد توجيه 302 ثم 200 للصفحة الرئيسية)
        if response.status_code != 200 or "Please enter a correct" in response.text:
            print(f"❌ Bot {user_id}: Login Failed")
            return

        # ---------------------------------------------------------
        # 3. استخراج Session ID من كود HTML لصفحة الشات
        # ---------------------------------------------------------
        # نذهب لصفحة الشات
        chat_page = session.get(CHAT_URL)
        html_content = chat_page.text
        
        # نبحث عن السطر: sessionId: "xxxxxxxx-xxxx-...."
        # باستخدام Regular Expression
        match = re.search(r'sessionId:\s*"([a-f0-9\-]+)"', html_content)
        
        if not match:
            print(f"❌ Bot {user_id}: Could not find Session UUID in HTML")
            return
            
        session_uuid = match.group(1)
        print(f"✅ Bot {user_id}: Logged in (Session: {session_uuid})")

        # ---------------------------------------------------------
        # 4. إرسال نص (عبر WebSocket)
        # ---------------------------------------------------------
        # ملاحظة: السكربت هنا يحتاج لتشغيل دالة async داخل thread
        # للتبسيط في هذا الاختبار، سنكتفي بالصور، أو نستخدم مكتبة websocket-client المتزامنة
        # لكن سنركز هنا على الصور لأنها الأهم لاختبار Azure
        
        # ---------------------------------------------------------
        # 5. إرسال صورة (تفعيل Azure GPT-4o) - لأول 5 فقط
        # ---------------------------------------------------------
        if user_id < NUM_IMAGE_SENDERS:
            with open('test.jpg', 'rb') as img:
                files = {'image': img}
                # View الرفع التقليدي يتوقع session_id في الـ POST
                data = {
                    'session_id': session_uuid,
                    'csrfmiddlewaretoken': session.cookies['csrftoken']
                }
                
                # إرسال الطلب (مع Referer و CSRF لأنها View محمية)
                headers = {'Referer': CHAT_URL}
                
                upload_res = session.post(
                    UPLOAD_URL, 
                    files=files, 
                    data=data, 
                    headers=headers
                )
                
                if upload_res.status_code == 200:
                    print(f"📸 Bot {user_id}: Image Uploaded (AI Analyzing...)")
                else:
                    print(f"❌ Bot {user_id}: Upload Failed {upload_res.status_code}")

    except Exception as e:
        print(f"💀 Bot {user_id} Error: {e}")

# --- تشغيل الهجوم ---
print(f"🚀 STARTING WEB-BASED STRESS TEST")
print(f"👥 Users: {NUM_USERS}")
print(f"📸 Image Uploads: {NUM_IMAGE_SENDERS}")
print("-" * 30)

threads = []
start_time = time.time()

for i in range(NUM_USERS):
    t = threading.Thread(target=bot_task, args=(i,))
    threads.append(t)
    t.start()
    time.sleep(0.2) # تأخير بسيط جداً لمحاكاة البشر

for t in threads:
    t.join()

print("-" * 30)
print(f"🏁 Test Finished in {time.time() - start_time:.2f} seconds")