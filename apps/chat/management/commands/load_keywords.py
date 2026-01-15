from django.core.management.base import BaseCommand
from apps.chat.models import DangerKeyword

class Command(BaseCommand):
    help = 'Loads medical triage keywords into the database'

    def handle(self, *args, **kwargs):
        # 1. قائمة الكلمات الخطرة (للطبيب فقط)
        # ملاحظة: لم نضف كلمات الممرض لأن النظام يعتبر أي شيء غير موجود هنا حالة "ممرض" افتراضياً
        DOCTOR_KEYWORDS = [
            # نزيف
            "blod", "blødning", "blør", "kraftig blødning",
            "indre blødning", "sår", "dyp sår", "skadet",
            
            # ألم حاد / صدر
            "brystsmerter", "sterk smerte", "akutt smerte",
            "trykk i brystet", "hjertesmerter", "hjerteinfarkt",
            
            # دوخة / وعي
            "svimmel", "besvimelse", "mistet bevissthet",
            "svartnet", "kollapset", "bevisstløs",
            
            # تقيؤ
            "oppkast", "kaster opp", "blodig oppkast",
            "sterk kvalme", "magesmerter",
            
            # حمل
            "gravid", "svangerskap", "graviditet",
            "abort", "blødning under graviditet", "rier",
            
            # تنفس
            "pustevansker", "vanskelig å puste",
            "kortpustet", "puster dårlig", "kvelning",
            
            # حرارة / عدوى
            "høy feber", "feber over 39",
            "infeksjon", "betennelse", "sepsis",
            
            # أعصاب
            "lammelse", "nummenhet", "kramper",
            "epilepsi", "slag", "hjerneblødning",
            
            # نفسية
            "selvmord", "selvskading",
            "vil dø", "skadet meg selv", "suicid",
            
            # كلمات عامة للطوارئ
            "hjelp", "akutt", "nød", "ambulanse", "dø", "døende"
        ]

        self.stdout.write(self.style.WARNING(f'Starting to import {len(DOCTOR_KEYWORDS)} keywords...'))

        count = 0
        for word in DOCTOR_KEYWORDS:
            # تنظيف الكلمة (أحرف صغيرة + إزالة مسافات)
            clean_word = word.lower().strip()
            
            # استخدام get_or_create لمنع التكرار إذا شغلت السكربت مرتين
            obj, created = DangerKeyword.objects.get_or_create(word=clean_word)
            
            if created:
                count += 1
                # self.stdout.write(f'- Added: {clean_word}') # ألغِ التعليق لرؤية التفاصيل

        self.stdout.write(self.style.SUCCESS(f'Successfully added {count} new keywords!'))
        self.stdout.write(self.style.SUCCESS(f'Total keywords in DB: {DangerKeyword.objects.count()}'))