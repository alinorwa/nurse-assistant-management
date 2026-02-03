import base64
import logging
import hashlib
import os
from openai import AzureOpenAI
from django.conf import settings
from django.core.files import File as DjangoFile # ضروري لحفظ ملف الصورة

logger = logging.getLogger(__name__)

class MedicalImageAnalyzer:
    def __init__(self):
        self.api_key = getattr(settings, 'AZURE_OPENAI_KEY', None)
        self.endpoint = getattr(settings, 'AZURE_OPENAI_ENDPOINT', None)
        
        if self.api_key and self.endpoint:
            self.client = AzureOpenAI(
                api_key=self.api_key,  
                api_version="2024-02-15-preview", 
                azure_endpoint=self.endpoint
            )
        else:
            self.client = None
            
        self.deployment_name = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')

    def calculate_hash(self, image_path):
        """حساب بصمة فريدة للصورة (SHA-256)"""
        sha256_hash = hashlib.sha256()
        with open(image_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def encode_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Image encoding error: {e}")
            return None

    def analyze(self, image_path):
        # استيراد المودل هنا لتجنب Circular Import
        from apps.chat.models import ImageAnalysisCache

        if not self.client:
            return "⚠️ AI Service Not Configured."

        # 1. حساب البصمة والبحث في الكاش (التوفير)
        img_hash = None
        try:
            img_hash = self.calculate_hash(image_path)
            # نبحث عن الهاش فقط
            cached_entry = ImageAnalysisCache.objects.filter(image_hash=img_hash).first()
            
            if cached_entry:
                logger.info(f"🚀 Image Analysis Cache HIT: {img_hash[:10]}")
                return cached_entry.analysis_result
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")

        # 2. التجهيز والإرسال لـ Azure
        encoded_image = self.encode_image(image_path)
        if not encoded_image:
            return "⚠️ Could not read image file."

        try:
            prompt = """
            You are a professional medical triage assistant. 
            Analyze this image provided by a refugee patient.
            Output Format (in Norwegian):
            - **Funn:** [Description]
            - **Mulig årsak:** [Condition]
            - **Anbefaling:** [Action]
            End with: "⚠️ AI-analyse kun for støtte. Kontakt lege for diagnose."
            """

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    { "role": "system", "content": "You are a helpful medical AI assistant." },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                        ],
                    }
                ],
                max_tokens=400,
                timeout=20
            )
            
            result_text = response.choices[0].message.content

            # 3. حفظ النتيجة + الصورة في الكاش (Code Updated)
            if img_hash:
                try:
                    with open(image_path, 'rb') as f:
                        ImageAnalysisCache.objects.create(
                            image_hash=img_hash,
                            analysis_result=result_text,
                            # حفظ نسخة من الصورة للمراجعة
                            cached_image=DjangoFile(f, name=os.path.basename(image_path))
                            # 🛑 تم حذف الحقول الزائدة (source_language, target_language) من هنا
                        )
                except Exception as db_err:
                    logger.error(f"Failed to save image cache: {db_err}")

            return result_text

        except Exception as e:
            logger.error(f"Image Analysis Failed: {e}")
            return "⚠️ AI Analysis temporarily unavailable."