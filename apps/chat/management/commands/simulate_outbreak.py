from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.chat.models import ChatSession, Message
from apps.chat.tasks import check_epidemic_outbreak
import random



# ... (نفس الاستيرادات)

class Command(BaseCommand):
    help = 'Simulates a Gastrointestinal outbreak'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('☣️  Starting Epidemic Simulation...'))
        
        fake_names = ["Ahmed Ali", "Sara O.", "Mohamed K.", "Ivan Petrov", "Fatima Hassan", "John Doe"]
        triggers = ["Jeg har oppkast", "Kraftig diaré", "Kvalme og magesmerter"]

        for i, name in enumerate(fake_names):
            username = f"demo_patient_{i+1}"
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"full_name": name, "role": "REFUGEE", "native_language": "ar"}
            )

            # 1. جلب الجلسة وتحديث أولويتها للأحمر (Doctor)
            session, _ = ChatSession.objects.get_or_create(refugee=user)
            session.priority = 2 # 🚨 DOCTOR
            session.save() # حفظ التغيير

            # 2. إنشاء الرسالة (وجعلها طارئة)
            Message.objects.create(
                session=session,
                sender=user,
                text_original="أشعر بغثيان شديد",
                text_translated=f"{random.choice(triggers)} (Simulated)", 
                is_urgent=True, # 🚨 Urgent
                timestamp=timezone.now()
            )
            
            self.stdout.write(f" - Patient {name} reported sickness.")

        self.stdout.write(self.style.SUCCESS(f'✅ Created 6 urgent cases.'))
        
        # 3. تشغيل الفحص
        self.stdout.write(self.style.WARNING('🔍 Running Analysis Task...'))
        check_epidemic_outbreak() # الآن سيعمل لأننا نقرأ بعد فك التشفير
        self.stdout.write(self.style.SUCCESS('🚀 Done.'))