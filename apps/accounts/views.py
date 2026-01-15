from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.shortcuts import redirect
from .forms import RefugeeRegistrationForm

class RefugeeRegisterView(CreateView):
    template_name = 'accounts/register.html'
    form_class = RefugeeRegistrationForm
    success_url = reverse_lazy('home') # التوجيه بعد النجاح

    def form_valid(self, form):
        # 1. حفظ المستخدم في قاعدة البيانات
        user = form.save()
        
        # 2. تسجيل الدخول مباشرة (Auto-Login)
        login(self.request, user , backend='django.contrib.auth.backends.ModelBackend')
        
        # 3. التوجيه للصفحة الرئيسية
        return redirect(self.success_url)

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True # إذا كان مسجلاً، لا تفتح صفحة الدخول
    
    # def get_success_url(self):
    #     return reverse_lazy('home')