from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models.functions import Now
from .models import Message, ChatSession
from .tasks import process_message_ai
from .services.triage_service import TriageService

@receiver(post_save, sender=Message)
def message_post_save(sender, instance, created, **kwargs):
    """
    مراقب الحفظ: يوزع المهام ويحدث الجلسة
    """
    
    # 1. تحديث وقت الجلسة (لترتيب المحادثات)
    if instance.session_id:
        ChatSession.objects.filter(id=instance.session_id).update(last_activity=Now())

    # متغيرات لتحديد هوية المرسل
    is_nurse = instance.sender.is_staff
    is_refugee = instance.sender.role == 'REFUGEE'

    # 2. منطق الممرض (De-escalation)
    if is_nurse:
        TriageService.deescalate_session(instance.session_id)
        # 🛑 التصحيح: حذفنا الـ return من هنا لنسمح بالترجمة بالأسفل

    # 3. شروط تشغيل المعالجة الخلفية (Celery)
    
    # الشرط أ: اللاجئ أرسل رسالة (تحتاج ترجمة أو تحليل صورة أو فرز طبي)
    refugee_needs_processing = (
        is_refugee and (
            (instance.text_original and not instance.text_translated) or
            (instance.image and not instance.ai_analysis)
        )
    )

    # الشرط ب: الممرض أرسل رسالة (تحتاج ترجمة فقط لتصل للاجئ بلغته)
    nurse_needs_translation = (
        is_nurse and 
        instance.text_original and 
        not instance.text_translated
    )

    # 4. التنفيذ
    if refugee_needs_processing or nurse_needs_translation:
        # نستخدم on_commit لضمان أن البيانات حُفظت قبل أن يبدأ الـ Worker
        transaction.on_commit(lambda: process_message_ai.delay(str(instance.id)))