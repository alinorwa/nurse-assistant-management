from django.core.management.base import BaseCommand
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Creates dummy users with mixed languages and emails for stress testing'

    def handle(self, *args, **kwargs):
        # قائمة اللغات (بنفس الترتيب الذي سنستخدمه في سكربت الهجوم)
        LANGUAGES = ['ar', 'uk', 'so', 'ti', 'en']
        
        # TOTAL_BOTS = 100
        TOTAL_BOTS = 50
        count = 0

        self.stdout.write(self.style.WARNING(f'Creating {TOTAL_BOTS} bots with mixed languages...'))

        for i in range(TOTAL_BOTS):
            username = f"stress_user_{i}"
            # إضافة إيميل وهمي فريد لكل مستخدم لتجنب خطأ قاعدة البيانات
            email = f"stress_user_{i}@example.com"
            
            # اختيار اللغة بناءً على الدور
            lang_code = LANGUAGES[i % len(LANGUAGES)]
            
            # التحقق من عدم وجود المستخدم أو الإيميل مسبقاً
            if not User.objects.filter(username=username).exists() and not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    username=username, 
                    email=email,  # <--- الإضافة الجديدة
                    password="123", 
                    full_name=f"Bot {i} ({lang_code})", 
                    role="REFUGEE",
                    native_language=lang_code 
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully created {count} new bots with emails and diverse languages!'))