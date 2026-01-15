from django.urls import path # لاحظ استوردنا path بدلاً من re_path
from . import consumers

websocket_urlpatterns = [
    # استخدام محول uuid الجاهز من جانغو
    # هذا يغنيك عن كتابة Regex ويقبل الشرطات (-) تلقائياً
    path('ws/chat/<uuid:session_id>/', consumers.ChatConsumer.as_asgi()),
]