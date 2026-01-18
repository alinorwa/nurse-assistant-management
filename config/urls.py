from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='/admin/'), name='admin_logout'),
    path('admin/', admin.site.urls),
    
    # الروابط الأساسية للموقع (ويب فقط)
    path('auth/', include('apps.accounts.urls')),
    path('chat/', include('apps.chat.urls')),
    path('', include('apps.core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)