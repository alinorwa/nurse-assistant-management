from celery import shared_task
from .models import Message, ChatSession, DangerKeyword
from apps.core.services import AzureTranslator
from apps.core.vision_analysis import MedicalImageAnalyzer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from PIL import Image as PilImage # لاستخدام ضغط الصور
import logging
import os

logger = logging.getLogger(__name__)

@shared_task
def process_message_ai(message_id):
    try:
        message = Message.objects.get(id=message_id)
        updates = {}
        should_save = False
        
        # === 1. ضغط الصورة (في الخلفية الآن) ===
        if message.image:
            try:
                # نفتح الصورة من المسار الفعلي
                img_path = message.image.path
                if os.path.exists(img_path):
                    im = PilImage.open(img_path)
                    
                    # تحويل الألوان إذا لزم الأمر
                    if im.mode in ('RGBA', 'P'):
                        im = im.convert('RGB')
                    
                    # التصغير (Resize)
                    im.thumbnail((1024, 1024), PilImage.Resampling.LANCZOS)
                    
                    # الحفظ فوق الملف الأصلي (Overwrite) بضغط عالٍ
                    im.save(img_path, format='JPEG', quality=70, optimize=True)
                    logger.info(f"Image compressed successfully for msg {message_id}")
            except Exception as e:
                logger.error(f"Image Compression Error: {e}")

        # === 2. الترجمة (كما هي) ===
        if message.text_original and not message.text_translated:
            try:
                translator = AzureTranslator()
                target_lang = 'no' if message.sender.role == 'REFUGEE' else message.session.refugee.native_language
                
                translation = translator.translate(
                    message.text_original, 
                    message.language_code or 'en', 
                    target_lang
                )
                message.text_translated = translation
                should_save = True
            except Exception as e:
                logger.error(f"Translation Error: {e}")

        # === 3. تحليل الصورة (Azure AI) ===
        if message.image and not message.ai_analysis:
            try:
                analyzer = MedicalImageAnalyzer()
                # نرسل الصورة (التي تم ضغطها للتو)
                analysis = analyzer.analyze(message.image.path)
                message.ai_analysis = analysis
                should_save = True
                
                alert_keywords = ["blood", "blod", "emergency", "akutt", "urgent"]
                if any(k in analysis.lower() for k in alert_keywords):
                    message.is_urgent = True
                    ChatSession.objects.filter(id=message.session.id).update(priority=2)

            except Exception as e:
                logger.error(f"Vision Error: {e}")

        # === 4. Triage للنص ===
        if message.sender.role == 'REFUGEE' and message.text_translated:
             danger_words = list(DangerKeyword.objects.filter(is_active=True).values_list('word', flat=True))
             if any(word in message.text_translated.lower() for word in danger_words):
                 message.is_urgent = True
                 ChatSession.objects.filter(id=message.session.id).update(priority=2)
                 should_save = True

        # === 5. الحفظ والإشعار ===
        if should_save:
            message.save()
            
            # إرسال التحديث للواجهة
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{message.session.id}',
                {
                    'type': 'chat_message',
                    'id': str(message.id),
                    'sender_id': message.sender.id,
                    'text_original': message.text_original,
                    'text_translated': message.text_translated,
                    'ai_analysis': message.ai_analysis,
                    'image_url': message.image.url if message.image else None,
                    'timestamp': str(message.timestamp.strftime("%H:%M")),
                }
            )

    except Message.DoesNotExist:
        logger.error("Message not found")
    except Exception as e:
        logger.error(f"Critical Task Error: {e}")