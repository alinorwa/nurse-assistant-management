import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from asgiref.sync import sync_to_async # نحتاجه فقط للكاش حالياً
from .models import ChatSession, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # استلام UUID من الرابط
            self.session_id = str(self.scope['url_route']['kwargs']['session_id'])
            self.room_group_name = f'chat_{self.session_id}'
            
            self.user = self.scope.get("user")

            # === التحقق من المستخدم (أسلوب Django الحديث) ===
            if not self.user or self.user.is_anonymous:
                # استخدام aget() الحديثة (Native Async)
                # بدلاً من database_sync_to_async
                try:
                    session = await ChatSession.objects.aget(id=self.session_id)
                    # ملاحظة: العلاقات (Foreign Keys) لا تزال تحتاج معالجة خاصة أحياناً
                    # لكن هنا سنستخدم خدعة بسيطة لجلب اللاجئ بشكل غير متزامن
                    self.user = await sync_to_async(lambda: session.refugee)()
                except ChatSession.DoesNotExist:
                    self.user = None

            if not self.user:
                print(f"❌ Unauthorized WebSocket attempt for session: {self.session_id}")
                await self.close()
                return

            # قبول الاتصال
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"✅ WebSocket Connected (Async): User {self.user.id}")
            
        except Exception as e:
            print("❌ Error during connect:", e)
            traceback.print_exc()
            await self.close()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except:
            pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_text = data.get('message', '').strip()
            user = self.user

            if not message_text:
                return

            # --- Throttling (Redis Cache لا يزال Sync فنستخدم Wrapper) ---
            if not user.is_staff:
                cache_key = f"throttle_user_{user.id}"
                LIMIT = 10000 
                PERIOD = 60 

                current_count = await sync_to_async(cache.get_or_set)(cache_key, 0, timeout=PERIOD)
                if current_count >= LIMIT:
                    await self.send(text_data=json.dumps({
                        'error': 'Please slow down. You are sending too fast.',
                        'type': 'error_alert'
                    }))
                    return
                await sync_to_async(cache.incr)(cache_key)

            # --- الحفظ والإرسال (Django Modern Async ORM) ---
            
            # 1. جلب الجلسة باستخدام aget
            session = await ChatSession.objects.aget(id=self.session_id)

            # 2. إنشاء الرسالة باستخدام acreate
            # هذا يستبدل الحاجة لدالة save_message المنفصلة
            saved_message = await Message.objects.acreate(
                session=session,
                sender=user,
                text_original=message_text
            )

            # ملاحظة هامة: acreate ستستدعي save() الخاصة بنا تلقائياً،
            # وبما أن save() تحتوي على كود Celery، كل شيء سيعمل بتناغم.

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'id': str(saved_message.id),
                    'sender_id': user.id,
                    'text_original': saved_message.text_original,
                    'text_translated': saved_message.text_translated,
                    'timestamp': str(saved_message.timestamp.strftime("%H:%M")),
                }
            )
        
        except Exception as e:
            print("❌ Error in receive:")
            traceback.print_exc()

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))