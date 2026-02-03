import sys
import os
from io import BytesIO
from PIL import Image as PilImage
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging

logger = logging.getLogger(__name__)

class ImageService:
    @staticmethod
    def compress_image(image_field):
        """
        تقوم بضغط الصورة المرفقة وتعديلها في الذاكرة (In-place).
        """
        if not image_field:
            return

        try:
            # فتح الصورة
            if hasattr(image_field, 'path') and os.path.exists(image_field.path):
                # إذا كانت محفوظة على القرص
                im = PilImage.open(image_field.path)
                save_path = image_field.path
                in_memory = False
            else:
                # إذا كانت في الذاكرة (قبل الحفظ)
                im = PilImage.open(image_field)
                in_memory = True

            # تحويل الألوان
            if im.mode in ('RGBA', 'P'):
                im = im.convert('RGB')

            # التصغير
            im.thumbnail((1024, 1024), PilImage.Resampling.LANCZOS)

            # الحفظ
            if in_memory:
                output = BytesIO()
                im.save(output, format='JPEG', quality=70, optimize=True)
                output.seek(0)
                return InMemoryUploadedFile(
                    output, 'ImageField', 
                    f"{image_field.name.split('.')[0]}.jpg", 
                    'image/jpeg', sys.getsizeof(output), None
                )
            else:
                # حفظ فوق الملف الأصلي
                im.save(save_path, format='JPEG', quality=70, optimize=True)
                logger.info("Image compressed successfully on disk.")

        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return image_field # إعادة الأصل في حال الفشل