import asyncio
import websockets
import requests
import json
import time
import random
import re

# الإعدادات
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/auth/login/"
CHAT_URL = f"{BASE_URL}/chat/"

# إعدادات الهجوم
TOTAL_USERS = 100        # عدد البوتات المتوفرة
MESSAGES_PER_USER = 25  # عدد الرسائل لكل مستخدم (20 * 25 = 500 رسالة)
DELAY_BETWEEN_MSGS = 0.5 # تأخير بسيط جداً لتجنب حظر الشبكة المحلية فوراً

# قاموس الرسائل
SAFE_MESSAGES = ["Hello", "How are you", "I want an appointment", "Thank you", "When is the doctor?"]
DANGER_MESSAGES = ["I feel heavy bleeding", "Chest pain", "I can't breathe", "Blood is coming out of my mouth", "I'm fainting"]

async def user_attack(user_index):
    username = f"stress_user_{user_index}"
    password = "123"
    session = requests.Session()

    print(f"🤖 Bot {user_index}: Connecting...")

    # 1. Login & Get Session UUID
    try:
        # Get CSRF
        session.get(LOGIN_URL)
        csrftoken = session.cookies['csrftoken']
        
        # Post Login
        login_res = session.post(
            LOGIN_URL, 
            data={'username': username, 'password': password, 'csrfmiddlewaretoken': csrftoken},
            headers={'Referer': LOGIN_URL}
        )
        
        # Get Chat Page to find UUID
        chat_page = session.get(CHAT_URL)
        match = re.search(r'sessionId:\s*"([a-f0-9\-]+)"', chat_page.text)
        if not match:
            print(f"❌ Bot {user_index}: Failed to get Session ID")
            return
        
        session_uuid = match.group(1)
        
        # 2. WebSocket Connection
        ws_url = f"ws://127.0.0.1:8000/ws/chat/{session_uuid}/"
        
        async with websockets.connect(ws_url) as websocket:
            for i in range(MESSAGES_PER_USER):
                # اختيار عشوائي: 20% رسائل خطرة
                if random.random() < 0.2:
                    text = random.choice(DANGER_MESSAGES)
                    msg_type = "🚨 DANGER"
                else:
                    text = random.choice(SAFE_MESSAGES)
                    msg_type = "✅ SAFE"

                msg_data = {"message": f"{text} ({i})"}
                
                await websocket.send(json.dumps(msg_data))
                print(f"📤 Bot {user_index}: Sent {msg_type} - {i}")
                
                # انتظار الرد للتأكد أن السيرفر استلمها (اختياري)
                # response = await websocket.recv() 
                
                await asyncio.sleep(DELAY_BETWEEN_MSGS)

    except Exception as e:
        print(f"💀 Bot {user_index} Error: {e}")

async def main():
    total_msgs = TOTAL_USERS * MESSAGES_PER_USER
    print(f"🚀 STARTING MASSIVE ATTACK: {total_msgs} Messages")
    print(f"🔥 Target: Localhost | Concurrency: {TOTAL_USERS} Users")
    
    start_time = time.time()
    
    tasks = []
    for i in range(TOTAL_USERS):
        tasks.append(user_attack(i))
    
    await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"\n🏁 Finished in {duration:.2f} seconds")
    print(f"📊 Speed: {total_msgs / duration:.2f} messages/second")

if __name__ == "__main__":
    asyncio.run(main())