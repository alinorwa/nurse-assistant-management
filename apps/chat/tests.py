from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch  # أداة المحاكاة (Mocking)
from .models import ChatSession, Message, DangerKeyword
from .tasks import process_message_ai  # نستورد المهمة لتشغيلها يدوياً

User = get_user_model()

class TriageSystemTest(TestCase):
    def setUp(self):
        """تجهيز البيانات قبل كل اختبار"""
        # 1. إنشاء المستخدمين
        self.refugee = User.objects.create_user(
            username="refugee_test", 
            password="123", 
            role="REFUGEE", 
            native_language="ar",
            full_name="Refugee User"
        )
        self.nurse = User.objects.create_user(
            username="nurse_test", 
            password="123", 
            role="NURSE", 
            is_staff=True,
            full_name="Nurse User"
        )
        
        # 2. إضافة كلمة خطرة للتجربة
        DangerKeyword.objects.create(word="blod", is_active=True)
        
        # 3. إنشاء جلسة
        self.session = ChatSession.objects.create(refugee=self.refugee, nurse=self.nurse)

    # نستخدم @patch لمنع الاتصال الحقيقي بـ Azure أثناء الاختبار
    @patch('apps.core.services.AzureTranslator.translate') 
    def test_normal_message_flow(self, mock_translate):
        """
        اختبار 1: رسالة عادية لا تحتوي خطراً.
        النتيجة المتوقعة: تظل الأولوية 1 (Nurse).
        """
        # إعداد رد المترجم الوهمي (نرويجي عادي)
        mock_translate.return_value = "Hei, hvordan går det?" 

        # 1. اللاجئ يرسل رسالة
        msg = Message.objects.create(
            session=self.session,
            sender=self.refugee,
            text_original="مرحبا"
        )

        # 2. محاكاة عمل Celery (نشغل المهمة يدوياً)
        process_message_ai(str(msg.id))
        
        # 3. التحقق من النتائج
        self.session.refresh_from_db()
        self.assertEqual(self.session.priority, 1) # يجب أن تبقى عادية

    @patch('apps.core.services.AzureTranslator.translate')
    def test_urgent_message_escalation(self, mock_translate):
        """
        اختبار 2: رسالة خطرة (تحتوي كلمة Blod).
        النتيجة المتوقعة: تتحول الأولوية إلى 2 (Doctor).
        """
        # إعداد رد المترجم الوهمي (يحتوي كلمة خطرة)
        mock_translate.return_value = "Jeg har mye blod" 

        # 1. اللاجئ يرسل رسالة خطرة
        msg = Message.objects.create(
            session=self.session,
            sender=self.refugee,
            text_original="لدي دم كثير"
        )

        # 2. محاكاة عمل Celery
        process_message_ai(str(msg.id))
        
        # 3. التحقق
        self.session.refresh_from_db()
        msg.refresh_from_db()
        
        self.assertTrue(msg.is_urgent) # الرسالة تم تمييزها كطارئة
        self.assertEqual(self.session.priority, 2) # الجلسة تحولت لطبيب

    def test_nurse_reply_deescalation(self):
        """
        اختبار 3: رد الممرض.
        النتيجة المتوقعة: تعود الأولوية إلى 1 فوراً (بدون Celery).
        """
        # أولاً: نرفع حالة الجلسة يدوياً إلى طارئة
        self.session.priority = 2
        self.session.save()
        
        # ثانياً: الممرض يرد
        # (المنطق هنا موجود داخل models.py save() لذا لا نحتاج لمحاكاة Celery)
        Message.objects.create(
            session=self.session,
            sender=self.nurse,
            text_original="Det går bra"
        )
        
        # ثالثاً: التحقق
        self.session.refresh_from_db()
        self.assertEqual(self.session.priority, 1) # يجب أن تعود خضراء