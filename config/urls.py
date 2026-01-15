from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static # تأكد من استيراد هذا
from django.contrib.auth import views as auth_views # 1. استيراد فيوز المصادقة
from apps.chat.api import api

urlpatterns = [
    # 2. الحل هنا: نضيف رابط خروج مخصص للأدمن قبل رابط الأدمن الرئيسي
    # هذا يجبر النظام: "عند خروج الأدمن، اذهب للصفحة /admin/ مرة أخرى (التي ستطلب الدخول)"
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='/admin/'), name='admin_logout'),
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path('auth/', include('apps.accounts.urls')),
    path('chat/', include('apps.chat.urls')),
    path('', include('apps.core.urls')),
]

# === الحل هنا: خدمة ملفات الميديا أثناء التطوير ===
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # هذا السطر هو المسؤول عن ظهور صور اللاجئين
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)