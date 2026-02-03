import requests
import time

# الرابط الحقيقي لصفحة الدخول (Web View)
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/auth/login/"

# بيانات مستخدم موجود فعلياً
USERNAME = "22" 
WRONG_PASSWORD = "wrong_password_123"

def run_brute_force():
    print(f"😈 The guessing attack begins on: {LOGIN_URL}")
    print("-" * 40)
    
    # نستخدم Session لكي نحتفظ بالكوكيز مثل المتصفح الحقيقي
    session = requests.Session()

    try:
        # 1. الخطوة الأولى: زيارة الصفحة لجلب CSRF Token
        # بدون هذه الخطوة، سيرفض جانغو الطلب فوراً (403 Forbidden)
        initial_response = session.get(LOGIN_URL)
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        else:
            print("❌ Failed to fetch CSRF Token. Is the server working?")
            return

        # 2. الخطوة الثانية: بدء الهجوم
        for i in range(1, 10):
            print(f" Attempt number {i}: ", end="")

            payload = {
                "username": USERNAME,
                "password": WRONG_PASSWORD,
                "csrfmiddlewaretoken": csrf_token  # لازم نرسل التوكن
            }
            
            # محاكاة هيدر Referer لأن جانغو يتحقق منه أحياناً
            headers = {"Referer": LOGIN_URL}

            response = session.post(LOGIN_URL, data=payload, headers=headers)
            
            # تحليل الرد
            # Django Login يعيد 200 عند الفشل (يعيد عرض الصفحة مع رسالة خطأ)
            # Django Axes يعيد 429 عند الحظر
            
            if response.status_code == 429: # Too Many Requests
                print("\n🔒 Blocked! (System Locked Out).")
                print("✅ Security test passed with flying colors.")
                print(f" Message from server: {response.reason}")
                break
            
            elif response.status_code == 200:
                # نتأكد أننا لم ندخل بالخطأ (إذا دخلنا سيعمل Redirect 302)
                if "Please enter a correct" in response.text or "Please enter" in response.text:
                    print("❌ Login failed (Incorrect password - normal).")
                else:
                    # قد يكون 200 ولكن الصفحة هي صفحة القفل (Lockout Page) التي صممناها
                    if "Account locked" in response.text or "locked" in response.text:
                        print("\n🔒 Blocked (custom lock screen appears)!")
                        print("✅ Security test passed.")
                        break
                    else:
                        print("⚠️ Mysterious reply (200 OK).")
            
            elif response.status_code == 403:
                print("⛔ CSRF Error (Script did not send token correctly).")
                break
                
    except Exception as e:
        print(f"\nConnection error: {e}")

if __name__ == "__main__":
    run_brute_force()