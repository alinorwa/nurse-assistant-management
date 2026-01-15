from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ChatSession, Message
# استيراد خدمة الترجمة (التي تحتوي على الكاش)
from apps.core.services import AzureTranslator 

@login_required
def chat_room(request):
    user = request.user
    
    # إذا كان ممرضاً، نوجهه للوحة التحكم
    if user.is_staff:
        return redirect('admin:index')
    
    # === منطق ترجمة رسالة الخصوصية (Dynamic GDPR Warning) ===
    # 1. النص الأساسي (الإنجليزية)
    base_warning = "🔒 For your privacy, do not write your name or health ID here. We identify you automatically."
    privacy_warning = base_warning 

    # 2. الترجمة الذكية (تعتمد على الكاش أولاً ثم Azure)
    if user.native_language and user.native_language != 'en':
        try:
            translator = AzureTranslator()
            # هذه الدالة ذكية: تبحث في TranslationCache أولاً
            # إذا وجدت الترجمة تجلبها (مجاناً وسريعاً)
            # إذا لم تجدها، تترجمها من Azure وتحفظها للمستقبل
            privacy_warning = translator.translate(
                text=base_warning,
                source_lang='en',
                target_lang=user.native_language
            )
        except Exception:
            # في حال فشل الاتصال، نكتفي بالرسالة الإنجليزية (Fail-safe)
            pass

    # 3. جلب الجلسة والرسائل
    session, created = ChatSession.objects.get_or_create(refugee=user)
    
    return render(request, 'chat/room.html', {
        'session': session,
        'chat_messages': session.messages.all(),
        # تمرير الرسالة المترجمة للقالب
        'privacy_warning': privacy_warning 
    })


@login_required
@require_POST
def upload_image(request):
    """API لاستقبال الصور من الشات"""
    user = request.user
    image_file = request.FILES.get('image')
    session_id = request.POST.get('session_id')

    if not image_file or not session_id:
        return JsonResponse({'error': 'No image or session provided'}, status=400)

    try:
        session = ChatSession.objects.get(id=session_id)
        
        # التأكد أن المستخدم طرف في هذه الجلسة
        if session.refugee != user and session.nurse != user:
             return JsonResponse({'error': 'Unauthorized'}, status=403)

        # حفظ الرسالة (سيتم ضغط الصورة تلقائياً بفضل المودل)
        message = Message.objects.create(
            session=session,
            sender=user,
            image=image_file,
            text_original="[Image Sent]" # نص بديل
        )

        # إشعار الويب سوكيت (Broadcasting)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{session.id}',
            {
                'type': 'chat_message',
                'id': str(message.id),
                'sender_id': user.id,
                'text_original': "", # لا يوجد نص للعرض
                'text_translated': "",
                'image_url': message.image.url, # نرسل الرابط
                'timestamp': str(message.timestamp.strftime("%H:%M")),
            }
        )

        return JsonResponse({'status': 'success', 'url': message.image.url})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)