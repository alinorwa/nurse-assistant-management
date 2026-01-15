import requests
import logging
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

class AzureTranslator:
    def __init__(self):
        self.api_key = getattr(settings, 'AZURE_TRANSLATOR_KEY', None)
        self.endpoint = getattr(settings, 'AZURE_TRANSLATOR_ENDPOINT', '')
        self.region = getattr(settings, 'AZURE_TRANSLATOR_REGION', 'global')
        
        if self.endpoint and not self.endpoint.endswith('/translate'):
            self.endpoint = f"{self.endpoint.rstrip('/')}/translate"

    def translate(self, text, source_lang, target_lang):
        # استيراد المودل هنا لتجنب Circular Import
        from apps.chat.models import TranslationCache

        # 1. فحوصات أولية
        if not text: return ""
        if source_lang == target_lang: return text
        
        # 2. البحث في الذاكرة (Cache) أولاً - لتوفير الفلوس
        try:
            text_hash = TranslationCache.make_hash(text)
            cached = TranslationCache.objects.filter(
                source_hash=text_hash,
                source_language=source_lang,
                target_language=target_lang
            ).first()
            
            if cached:
                return cached.translated_text
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        # 3. إذا لم نجدها، نطلب من Azure (مع حماية من الأخطاء)
        if not self.api_key or not self.endpoint:
            return f"{text} (Config Error)"

        try:
            path = '/translate'
            constructed_url = self.endpoint
            params = {
                'api-version': '3.0',
                'from': source_lang,
                'to': target_lang
            }
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key,
                'Ocp-Apim-Subscription-Region': self.region,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }
            body = [{'text': text}]

            # مهلة 5 ثواني فقط لكي لا يعلق السيرفر
            response = requests.post(constructed_url, params=params, headers=headers, json=body, timeout=5)
            response.raise_for_status()
            
            result = response.json()
            if result and len(result) > 0:
                translated_text = result[0]['translations'][0]['text']
                
                # حفظ النتيجة في الذاكرة للمستقبل
                try:
                    TranslationCache.objects.create(
                        source_hash=text_hash,
                        source_language=source_lang,
                        target_language=target_lang,
                        source_text=text,
                        translated_text=translated_text
                    )
                except Exception as db_err:
                    logger.error(f"Failed to save cache: {db_err}")

                return translated_text
            
        except requests.exceptions.Timeout:
            logger.error("Azure Translation Timeout.")
            return f"{text} (Connection Timeout)"
            
        except Exception as e:
            logger.error(f"Translation Failed: {e}")
            # في حال الفشل، نعيد النص الأصلي لضمان استمرار الشات
            return f"{text} (Translation Unavailable)"
        
        return text