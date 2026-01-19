from celery import shared_task
from .models import Message, ChatSession, DangerKeyword
from apps.core.services import AzureTranslator
from apps.core.vision_analysis import MedicalImageAnalyzer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from PIL import Image as PilImage # لاستخدام ضغط الصور
import logging
import os
# أضف هذه الاستيرادات في أعلى الملف إذا لم تكن موجودة
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

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


@shared_task
def check_epidemic_outbreak():
    from .models import EpidemicAlert, Message # استيراد داخلي

    # 1. تحديد النطاق الزمني (آخر 60 دقيقة)
    time_threshold = timezone.now() - timedelta(hours=1)
    
    # القاموس
    epidemic_signatures = {
        "Gastrointestinal (تسمم غذائي)": ["diaré", "oppkast", "kvalme", "magesmerter"],
        "Respiratory (تنفسي/إنفلونزا)": ["høy feber", "hoste", "tungpustet", "influensa"],
        "Skin (أمراض جلدية)": ["skabb", "utslett", "intens kløe"],
    }

    # حد الخطر
    DANGER_THRESHOLD = 5

    # 2. جلب رسائل اللاجئين في آخر ساعة (بدون فلترة النص في الداتا بيز)
    recent_messages = Message.objects.filter(
        timestamp__gte=time_threshold,
        sender__role='REFUGEE'
    ).select_related('session') # لتحسين الأداء

    # 3. الفحص اليدوي في الذاكرة (لأن النص مشفر)
    # سنقوم بإنشاء قاموس لتجميع الحالات: { 'Type': {set of user_ids} }
    detected_cases = {k: set() for k in epidemic_signatures.keys()}

    for msg in recent_messages:
        # فك التشفير يتم تلقائياً هنا عند استدعاء الحقل
        text_content = (msg.text_translated or "").lower() + " " + (msg.ai_analysis or "").lower()
        
        for category, keywords in epidemic_signatures.items():
            for word in keywords:
                if word in text_content:
                    # وجدنا عرضاً، نضيف رقم المستخدم (لعدم تكرار نفس الشخص)
                    detected_cases[category].add(msg.session.refugee.id)
                    break # وجدنا الكلمة، ننتقل للفئة التالية

    # 4. تسجيل التنبيهات
    for category, affected_users in detected_cases.items():
        count = len(affected_users)
        
        if count >= DANGER_THRESHOLD:
            # التحقق من عدم وجود تنبيه حديث لنفس السبب
            recent_alert = EpidemicAlert.objects.filter(
                symptom_category=category,
                timestamp__gte=time_threshold
            ).exists()

            if not recent_alert:
                EpidemicAlert.objects.create(
                    symptom_category=category,
                    case_count=count
                )
                
                # إشعار للأدمن
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_notifications",
                    {
                        "type": "epidemic_alert",
                        "category": category,
                        "count": count
                    }
                )