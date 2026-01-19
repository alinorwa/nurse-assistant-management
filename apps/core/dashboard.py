from django.views.generic import TemplateView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _

# استيراد المودلز
from apps.accounts.models import User
from apps.chat.models import ChatSession, EpidemicAlert

@method_decorator(staff_member_required, name='dispatch')
class MedicalDashboardView(TemplateView):
    template_name = "admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إعدادات العناوين لقالب Unfold
        context['title'] = "Medical Analytics / التحليل الطبي"
        context['subtitle'] = "نظرة عامة على حالة المخيم والنشاط اليومي"
        
        # 1. إحصائيات اللغات (Pie Chart)
        language_data = User.objects.filter(role='REFUGEE').values('native_language').annotate(total=Count('id'))
        
        lang_labels = []
        lang_counts = []
        lang_dict = dict(User.LANGUAGE_CHOICES)
        
        for item in language_data:
            code = item['native_language']
            label = lang_dict.get(code, code)
            lang_labels.append(label)
            lang_counts.append(item['total'])

        context['chart_languages'] = {
            "type": "doughnut",
            "data": {
                "labels": lang_labels,
                "datasets": [{
                    "data": lang_counts,
                    "backgroundColor": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
                    "borderWidth": 0
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {"legend": {"position": "bottom"}}
            }
        }

        # 2. النشاط اليومي لآخر 7 أيام (Line Chart)
        last_week = timezone.now() - timedelta(days=7)
        daily_sessions = ChatSession.objects.filter(start_time__gte=last_week)\
            .annotate(date=TruncDay('start_time'))\
            .values('date')\
            .annotate(count=Count('id'))\
            .order_by('date')
            
        context['chart_activity'] = {
            "type": "line",
            "data": {
                "labels": [item['date'].strftime('%Y-%m-%d') for item in daily_sessions],
                "datasets": [{
                    "label": "جلسات جديدة",
                    "data": [item['count'] for item in daily_sessions],
                    "borderColor": "#0ea5e9",
                    "backgroundColor": "rgba(14, 165, 233, 0.1)",
                    "fill": True,
                    "tension": 0.4
                }]
            }
        }

        # 3. الإنذارات الوبائية (Bar Chart)
        alerts = EpidemicAlert.objects.values('symptom_category').annotate(total_cases=Sum('case_count'))
        
        context['chart_epidemics'] = {
            "type": "bar",
            "data": {
                "labels": [item['symptom_category'] for item in alerts],
                "datasets": [{
                    "label": "عدد الحالات المشتبه بها",
                    "data": [item['total_cases'] for item in alerts],
                    "backgroundColor": "#ef4444",
                    "borderRadius": 4
                }]
            }
        }
        
        # KPIs
        context['kpi'] = {
            "total_refugees": User.objects.filter(role='REFUGEE').count(),
            "urgent_sessions": ChatSession.objects.filter(priority=2, is_active=True).count(),
            "active_now": ChatSession.objects.filter(is_active=True).count()
        }

        return context