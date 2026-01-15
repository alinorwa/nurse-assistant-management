from typing import List, Optional
from ninja import NinjaAPI, Schema, UploadedFile, File
from django.contrib.auth import authenticate, login, get_user_model
from django.shortcuts import get_object_or_404
from .models import ChatSession, Message
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings

User = get_user_model()

api = NinjaAPI(
    title="Refugee Medical API",
    description="API Backend for Flutter Mobile App",
    version="1.0.0"
)

# ==========================================
# 1. Schemas (شكل البيانات)
# ==========================================

class LoginInput(Schema):
    username: str
    password: str

class RegisterInput(Schema):
    username: str 
    password: str
    confirm_password: str 
    full_name: str
    native_language: str = "ar" 

class LoginSuccess(Schema):
    id: int
    full_name: str
    role: str
    session_uuid: str 

# --- (جديد) هيكل بيانات إرسال رسالة نصية ---
class SendMessageInput(Schema):
    session_id: str
    text: str

class MessageOut(Schema):
    id: str 
    text: str 
    is_me: bool 
    sender_name: str
    image_url: Optional[str] = None
    ai_analysis: Optional[str] = None 
    timestamp: str
    status: str 

class ErrorResponse(Schema):
    error: str

# ==========================================
# 2. Auth Endpoints
# ==========================================

@api.post("/auth/register", response={201: LoginSuccess, 400: ErrorResponse})
def user_register(request, data: RegisterInput):
    """إنشاء حساب جديد"""
    if data.password != data.confirm_password:
        return 400, {"error": "Passwords do not match"}

    if User.objects.filter(username=data.username).exists():
        return 400, {"error": "Health ID already exists"}

    try:
        user = User.objects.create_user(
            username=data.username,
            password=data.password,
            full_name=data.full_name,
            native_language=data.native_language,
            role="REFUGEE"
        )
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        chat_session, _ = ChatSession.objects.get_or_create(refugee=user)

        return 201, {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role,
            "session_uuid": str(chat_session.id)
        }
    except Exception as e:
        return 400, {"error": str(e)}


@api.post("/auth/login", response={200: LoginSuccess, 401: ErrorResponse})
def user_login(request, data: LoginInput):
    """تسجيل الدخول"""
    user = authenticate(request, username=data.username, password=data.password)
    
    if user is not None:
        login(request, user) 
        chat_session, _ = ChatSession.objects.get_or_create(refugee=user)
        
        return 200, {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role,
            "session_uuid": str(chat_session.id) 
        }
        
    return 401, {"error": "Invalid Credentials"}

# ==========================================
# 3. Chat Endpoints
# ==========================================

@api.get("/chat/history", response=List[MessageOut], auth=None)
def get_chat_history(request, session_id: str):
    """جلب الأرشيف"""
    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().order_by('timestamp')
    result = []
    current_user = request.user if request.user.is_authenticated else session.refugee

    for msg in messages:
        is_me = (msg.sender == current_user)
        if is_me:
            display_text = msg.text_original
        else:
            display_text = msg.text_translated if msg.text_translated else msg.text_original

        result.append({
            "id": str(msg.id),
            "text": display_text or "",
            "is_me": is_me,
            "sender_name": "ME" if is_me else "NURSE",
            "image_url": request.build_absolute_uri(msg.image.url) if msg.image else None,
            "ai_analysis": msg.ai_analysis if (msg.ai_analysis and not is_me) else None,
            "timestamp": msg.timestamp.strftime("%H:%M"),
            "status": "DOCTOR" if msg.is_urgent else "NURSE"
        })
    return result


@api.post("/chat/send")
def send_message(request, data: SendMessageInput):
    """
    (جديد) إرسال رسالة نصية من التطبيق
    """
    # 1. التحقق من الجلسة
    session = get_object_or_404(ChatSession, id=data.session_id)
    
    # 2. تحديد المستخدم (من التوكن أو الافتراضي للاجئ)
    user = request.user if request.user.is_authenticated else session.refugee

    if not data.text.strip():
        return {"error": "Message cannot be empty"}

    # 3. حفظ الرسالة
    # (هنا سيعمل المودل وسيقوم بتفعيل Celery للترجمة تلقائياً)
    msg = Message.objects.create(
        session=session,
        sender=user,
        text_original=data.text
    )

    # 4. إشعار الويب سوكيت (ليظهر للممرض فوراً)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{session.id}',
        {
            'type': 'chat_message',
            'id': str(msg.id),
            'sender_id': user.id,
            'text_original': msg.text_original,
            'text_translated': "", # لم تترجم بعد
            'timestamp': str(msg.timestamp.strftime("%H:%M")),
        }
    )

    return {"success": True, "message_id": str(msg.id)}


@api.post("/chat/upload")
def upload_file(request, session_id: str, file: UploadedFile = File(...)):
    """رفع صورة"""
    session = get_object_or_404(ChatSession, id=session_id)
    user = request.user if request.user.is_authenticated else session.refugee

    msg = Message.objects.create(
        session=session,
        sender=user,
        image=file,
        text_original="[Image from App]"
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{session.id}',
        {
            'type': 'chat_message',
            'id': str(msg.id),
            'sender_id': user.id,
            'text_original': "",
            'text_translated': "",
            'image_url': msg.image.url,
            'timestamp': str(msg.timestamp.strftime("%H:%M")),
        }
    )

    return {"success": True, "image_url": msg.image.url}




# ==========================================
# 4. Helper Endpoints (للمساعدة في التطوير)
# ==========================================

@api.get("/chat/get_session_id")
def get_session_by_username(request, username: str):
    """
    أداة مساعدة: ادخل الرقم الصحي واحصل على رقم الجلسة فوراً.
    (مفيد للتجربة والاختبار دون الحاجة لتسجيل الدخول كل مرة)
    """
    # البحث عن المستخدم
    user = get_object_or_404(User, username=username)
    
    # البحث عن جلسته
    session = ChatSession.objects.filter(refugee=user).first()
    
    if session:
        return {"session_uuid": str(session.id)}
    else:
        return 404, {"error": "لا توجد جلسة لهذا المستخدم"}