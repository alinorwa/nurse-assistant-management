from django.core.management.base import BaseCommand
from apps.chat.models import Message
from django.utils import timezone
from datetime import timedelta
import os

class Command(BaseCommand):
    help = 'Deletes chat images older than 30 days to save space and privacy'

    def handle(self, *args, **kwargs):
        # تحديد التاريخ: قبل 30 يوماً من الآن
        cutoff_date = timezone.now() - timedelta(days=14)
        
        # البحث عن الرسائل القديمة التي تحتوي على صور
        old_messages_with_images = Message.objects.filter(
            timestamp__lt=cutoff_date
        ).exclude(image='')

        count = 0
        for msg in old_messages_with_images:
            if msg.image:
                try:
                    # حذف الملف من الهارد ديسك
                    if os.path.isfile(msg.image.path):
                        os.remove(msg.image.path)
                    
                    # حذف الرابط من قاعدة البيانات (أو ترك رسالة "تم الحذف")
                    msg.image = None 
                    msg.save()
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error deleting image {msg.id}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old images.'))