from django.shortcuts import redirect, render
from django.views.generic import TemplateView

def root_redirect_view(request):
    """
    هذه الدالة هي بوابة النظام الرئيسية (/)
    تقرر أين يذهب المستخدم بناءً على حالته.
    """
    # 1. إذا لم يكن مسجلاً للدخول -> صفحة الدخول
    if not request.user.is_authenticated:
        return redirect('login')

    # 2. إذا كان ممرضاً (Admin/Staff) -> لوحة التحكم
    if request.user.is_staff:
        return redirect('admin:index')

    # 3. إذا كان لاجئاً -> صفحة الشات مباشرة
    return redirect('chat_room')

# (أبقِ على باقي الكلاسات مثل ServiceWorkerView كما هي)
class ServiceWorkerView(TemplateView):
    template_name = "sw.js"
    content_type = "application/javascript"

class OfflineView(TemplateView):
    template_name = "offline.html"