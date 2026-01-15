import base64
import logging
from openai import AzureOpenAI
from django.conf import settings

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

    def encode_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Image encoding error: {e}")
            return None

    def analyze(self, image_path):
        # حماية: إذا لم يكن Azure مهيئاً
        if not self.client:
            return "⚠️ AI Service Not Configured."

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
                timeout=20 # ننتظر 20 ثانية كحد أقصى للتحليل
            )
            
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Image Analysis Failed: {e}")
            # رسالة لطيفة للممرض بدلاً من انهيار النظام
            return "⚠️ AI Analysis temporarily unavailable."