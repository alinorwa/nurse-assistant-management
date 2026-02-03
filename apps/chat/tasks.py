from celery import shared_task
from .models import Message
# استيراد الخدمات
from apps.core.services import AzureTranslator
from apps.core.vision_analysis import MedicalImageAnalyzer
from .services.image_service import ImageService
from .services.triage_service import TriageService
from .services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_message_ai(message_id):
    try:
        # جلب الرسالة مع البيانات المرتبطة (لتسريع الاستعلام)
        message = Message.objects.select_related('session', 'sender', 'session__refugee').get(id=message_id)
        fields_to_update = []
        is_urgent_detected = False

        # 1. ضغط الصورة (على القرص)
        if message.image:
            ImageService.compress_image(message.image)

        # 2. الترجمة (التعديل هنا: السماح بالترجمة للطرفين)
        if message.text_original and not message.text_translated:
            translator = AzureTranslator()
            
            # تحديد اللغة الهدف بذكاء:
            # - إذا المرسل لاجئ -> نترجم للنرويجية (no)
            # - إذا المرسل ممرض -> نترجم للغة اللاجئ (native_language)
            if message.sender.role == 'REFUGEE':
                target_lang = 'no'
            else:
                target_lang = message.session.refugee.native_language

            # الترجمة
            translation = translator.translate(
                message.text_original, 
                message.language_code or 'en', 
                target_lang
            )
            
            message.text_translated = translation
            fields_to_update.append('text_translated')

            # فحص الخطر في الترجمة (فقط إذا كان المرسل لاجئاً)
            # الممرض لا يحتاج لفحص كلامه بحثاً عن الخطر
            if message.sender.role == 'REFUGEE':
                if TriageService.check_for_danger(translation):
                    is_urgent_detected = True

        # 3. تحليل الصورة (AI Vision) - للاجئ فقط
        if message.image and not message.ai_analysis:
            analyzer = MedicalImageAnalyzer()
            analysis = analyzer.analyze(message.image.path)
            message.ai_analysis = analysis
            fields_to_update.append('ai_analysis')

            # فحص الخطر في التحليل
            if TriageService.check_for_danger(analysis):
                is_urgent_detected = True

        # 4. تطبيق التحديثات (للأولوية)
        if is_urgent_detected:
            message.is_urgent = True
            fields_to_update.append('is_urgent')
            TriageService.escalate_session(message.session_id)

        # 5. الحفظ والإشعار
        if fields_to_update:
            message.save(update_fields=fields_to_update)
            # إرسال التحديث للجميع (ليظهر النص المترجم في الشات)
            NotificationService.broadcast_message_update(message)
            logger.info(f"Message {message_id} processed successfully.")

    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found.")
    except Exception as e:
        logger.error(f"Task processing error: {e}")




# ... (الكود السابق في الملف process_message_ai ... اترك كل شيء فوق كما هو)

# ==============================================================================
# 🦠 Epidemic Early Warning Task (الإضافة الجديدة)
# ==============================================================================

@shared_task
def check_epidemic_outbreak():
    from django.utils import timezone
    from datetime import timedelta
    from .models import EpidemicAlert, Message
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    # 1. تحديد النطاق الزمني (آخر ساعة)
    time_threshold = timezone.now() - timedelta(hours=1)
    
    # القاموس الطبي
    epidemic_signatures = {
        "Gastrointestinal ": ["diaré", "oppkast", "kvalme", "magesmerter"],
        "Respiratory ": ["høy feber", "hoste", "tungpustet", "influensa"],
        "Skin ": ["skabb", "utslett", "intens kløe"],
    }

    # حد الخطر (عدد الأشخاص)
    DANGER_THRESHOLD = 5

    # 2. جلب الرسائل (يجب جلبها لفك تشفيرها في الذاكرة)
    recent_messages = Message.objects.filter(
        timestamp__gte=time_threshold,
        sender__role='REFUGEE'
    ).select_related('session')

    # 3. الفحص اليدوي (لأن النصوص مشفرة)
    detected_cases = {k: set() for k in epidemic_signatures.keys()}

    for msg in recent_messages:
        # دمج النص المترجم وتحليل الذكاء الاصطناعي للبحث
        text_content = (msg.text_translated or "") + " " + (msg.ai_analysis or "")
        text_content = text_content.lower()
        
        for category, keywords in epidemic_signatures.items():
            for word in keywords:
                if word in text_content:
                    detected_cases[category].add(msg.session.refugee.id)
                    break 

    # 4. تسجيل التنبيهات
    for category, affected_users in detected_cases.items():
        count = len(affected_users)
        
        if count >= DANGER_THRESHOLD:
            # نتأكد من عدم تكرار التنبيه لنفس الفئة في نفس الساعة
            recent_alert = EpidemicAlert.objects.filter(
                symptom_category=category,
                timestamp__gte=time_threshold
            ).exists()

            if not recent_alert:
                EpidemicAlert.objects.create(
                    symptom_category=category,
                    case_count=count
                )
                
                # إشعار للأدمن (اختياري عبر الويب سوكيت)
                logger.critical(f"🚨 EPIDEMIC DETECTED: {category} ({count} cases)")        