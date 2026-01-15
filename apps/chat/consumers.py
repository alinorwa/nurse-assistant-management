import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from asgiref.sync import sync_to_async
from .models import ChatSession, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # استخدام str() هنا احتياطاً رغم أنه يأتي كنص من الرابط
            self.session_id = str(self.scope['url_route']['kwargs']['session_id'])
            self.room_group_name = f'chat_{self.session_id}'

            if self.scope["user"].is_anonymous:
                await self.close()
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        except Exception as e:
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
            user = self.scope['user']

            if not message_text:
                return

            # --- الحماية من الإغراق (Throttling) ---
            if not user.is_staff:
                cache_key = f"throttle_user_{user.id}"
                LIMIT = 30 
                PERIOD = 60 

                current_count = await sync_to_async(cache.get_or_set)(cache_key, 0, timeout=PERIOD)

                if current_count >= LIMIT:
                    await self.send(text_data=json.dumps({
                        'error': 'Please slow down. You are sending too fast.',
                        'type': 'error_alert'
                    }))
                    return

                await sync_to_async(cache.incr)(cache_key)

            # --- الحفظ والإرسال ---
            saved_message = await self.save_message(user, self.session_id, message_text)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    
                    # 🛑 التصحيح هنا: تحويل UUID إلى نص (String)
                    'id': str(saved_message.id),
                    'sender_id': user.id, # الـ User ID غالباً رقم، لكن لو كان UUID يجب تحويله أيضاً
                    
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

    @database_sync_to_async
    def save_message(self, user, session_id, text):
        session = ChatSession.objects.get(id=session_id)
        return Message.objects.create(session=session, sender=user, text_original=text)