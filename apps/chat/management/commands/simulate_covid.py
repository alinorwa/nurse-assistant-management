from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.chat.models import ChatSession, Message
from apps.chat.tasks import check_epidemic_outbreak
import random

class Command(BaseCommand):
    help = 'Simulates a COVID-19 / Respiratory outbreak for Demo purposes'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.ERROR('🦠  Starting COVID-19 / Respiratory Simulation...'))

        fake_names = [ "Lina Samer", "Yuri Volkov", "Omar Khalid", 
            "Maria Garcia", "Chen Wei", "Aisha Juma", "Fatima Hassan", "John Doe"]
        triggers = [
            "Jeg har høy feber",       # (حمى عالية) - تطابق تام
            "Jeg har kraftig hoste",   # (سعال) - تطابق كلمة hoste
            "Jeg er tungpustet",       # (ضيق تنفس) - تطابق تام
            "Tror jeg har influensa"   # (إنفلونزا) - تطابق تام
        ]

        created_count = 0

        for i, name in enumerate(fake_names):
            username = f"covid_patient_{i+1}"
            
            # --- التعديل هنا: إضافة إيميل وهمي فريد ---
            email = f"covid_{i+1}@example.com"

            # نستخدم update_or_create لضمان تحديث الإيميل إذا كان المستخدم موجوداً
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    "full_name": name,
                    "email": email, # <--- ضروري جداً
                    "role": "REFUGEE",
                    "native_language": "ar"
                }
            )

            # 2. إنشاء جلسة وتحديثها للطوارئ
            session, _ = ChatSession.objects.get_or_create(refugee=user)
            session.priority = 2 # 🚨 DOCTOR
            session.save()

            # 3. إرسال رسالة "مسمومة"
            Message.objects.create(
                session=session,
                sender=user,
                text_original="أعاني من أعراض تنفسية",
                text_translated=f"{random.choice(triggers)} (Simulated)", 
                is_urgent=True, 
                timestamp=timezone.now()
            )
            
            created_count += 1
            self.stdout.write(f" - Patient {name} reported symptoms.")

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully created {created_count}  COVID-suspected cases.'))

        # 4. تشغيل فحص الوباء
        self.stdout.write(self.style.WARNING('🔍 Running Epidemic Check Task...'))
        check_epidemic_outbreak()
        
        self.stdout.write(self.style.SUCCESS('🚀  DONE. Check Admin Panel -> Epidemic Alerts.'))