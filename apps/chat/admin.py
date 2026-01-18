from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import ChatSession, Message, TranslationCache, DangerKeyword
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from unfold.admin import ModelAdmin, TabularInline

@admin.register(DangerKeyword)
class DangerKeywordAdmin(ModelAdmin):
    list_display = ('word', 'is_active')
    search_fields = ('word',)
    help_text = "أضف الكلمات النرويجية الخطرة."

class MessageInline(TabularInline):
    model = Message
    extra = 1
    tab = True
    
    fields = ('sender_display', 'smart_content_display', 'status_and_time', 'text_original', 'image')
    readonly_fields = ('sender_display', 'smart_content_display', 'status_and_time')

    # --- 1. العمود الأوسط: المحتوى الذكي (نسخة نظيفة جداً) ---
    def smart_content_display(self, obj):
        content_parts = []
        
        # قائمة النصوص التي نريد إخفاءها لأنها مجرد تنبيهات للنظام
        IGNORED_TEXTS = [
            "[Image Sent]", 
            "[Image from App]", 
            "[bilde sendt]", 
            "[Image Sent from App]",
            ""
        ]

        # أ) النصوص
        if obj.sender_id:
            # للاجئ: نعرض الترجمة
            if obj.sender.role == 'REFUGEE':
                text_to_show = obj.text_translated.strip() if obj.text_translated else ""
                
                # الشرط الجديد: نعرض النص فقط إذا لم يكن في قائمة التجاهل
                if text_to_show and text_to_show not in IGNORED_TEXTS:
                    part = format_html(
                        '''
                        <div style="background-color: #eff6ff; padding: 12px; border-radius: 8px; border-left: 5px solid #3b82f6; color: #1e3a8a; margin-bottom: 10px; font-size: 1rem;">
                            <strong style="display:block; font-size:0.75rem; color:#60a5fa; margin-bottom:4px;">MELDING (Oversatt):</strong>
                            {}
                        </div>
                        ''',
                        text_to_show
                    )
                    content_parts.append(part)
            
            # للممرض: نعرض النص الأصلي
            else:
                text_to_show = obj.text_original.strip() if obj.text_original else ""
                
                if text_to_show and text_to_show not in IGNORED_TEXTS:
                    part = format_html(
                        '''
                        <div style="background-color: #f3f4f6; padding: 12px; border-radius: 8px; color: #374151; margin-bottom: 10px;">
                            {}
                        </div>
                        ''',
                        text_to_show
                    )
                    content_parts.append(part)

        # ب) الصور
        if obj.image:
            part = format_html(
                '''
                <div style="margin-top: 5px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 5px; background: white; width: fit-content;">
                    <a href="{url}" target="_blank" title="Click to open full size">
                        <img src="{url}" 
                             style="height: 200px; width: auto; max-width: 100%; border-radius: 5px; cursor: zoom-in;" 
                        />
                    </a>
                </div>
                ''',
                url=obj.image.url
            )
            content_parts.append(part)
        
        # 🛑 تم حذف (elif obj.pk) بالكامل لإزالة مربع "No Image"

        # ج) الذكاء الاصطناعي
        if obj.ai_analysis:
            part = format_html(
                '''
                <div style="background-color: #fffbeb; border: 1px solid #fcd34d; color: #92400e; padding: 10px; border-radius: 6px; font-size: 0.9em; margin-top: 10px;">
                    <strong style="display:block; margin-bottom:5px;">🤖 AI Insight:</strong>
                    {}
                </div>
                ''',
                obj.ai_analysis
            )
            content_parts.append(part)

        return mark_safe("".join(p for p in content_parts))
    
    smart_content_display.short_description = "Content / Innhold"

    # --- 2. العمود الأيمن ---
    def status_and_time(self, obj):
        if not obj.pk: return "-"
        
        if obj.is_urgent:
            bg_color = "#dc3545"
            label = "🚨 DOCTOR"
        else:
            bg_color = "#28a745"
            label = "✅ NURSE"

        return format_html(
            '''
            <div style="display: flex; flex-direction: column; gap: 8px; align-items: center; width: 100px;">
                <div style="
                    background-color: {bg}; 
                    color: white; 
                    padding: 8px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    text-align: center; 
                    width: 100%;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    {label}
                </div>
                <div style="text-align: center; color: #6b7280; font-size: 0.8rem; line-height: 1.4;">
                    <div style="font-weight: 600;">{time}</div>
                    <div>{date}</div>
                </div>
            </div>
            ''',
            bg=bg_color,
            label=label,
            time=obj.timestamp.strftime("%H:%M"),
            date=obj.timestamp.strftime("%d %b %Y")
        )
    status_and_time.short_description = "Status"

    # --- 3. العمود الأيسر ---
    def sender_display(self, obj):
        if not obj.sender_id: return "-"
        role_color = "#3b82f6" if obj.sender.role == "NURSE" else "#10b981"
        role_name = "NURSE" if obj.sender.is_staff else "REFUGEE"
        
        return format_html(
            '''
            <div style="font-weight: bold; color: {}; font-size: 1rem;">
                {}
                <div style="font-size: 0.75rem; color: #6b7280; font-weight: normal; margin-top:2px;">{}</div>
            </div>
            ''',
            role_color,
            role_name,
            obj.sender.full_name
        )
    sender_display.short_description = "Sender"

    list_fullwidth = True
    
    class Media:
        css = {
            'all': ('css/admin_chat_clean.css',) 
        }

@admin.register(ChatSession)
class ChatSessionAdmin(ModelAdmin):
    list_display = ('priority_flag', 'health_number_display', 'refugee_info', 'last_activity', 'is_active')
    list_filter = ('priority', 'is_active', 'start_time')
    inlines = [MessageInline]
    search_fields = ('refugee__full_name', 'refugee__username')
    readonly_fields = ('last_activity',)
    ordering = ('-priority', '-last_activity')
    list_fullwidth = True

    def health_number_display(self, obj):
        return obj.refugee.username
    health_number_display.short_description = "Health ID"
    health_number_display.admin_order_field = 'refugee__username'

    def refugee_info(self, obj):
        return f"{obj.refugee.full_name} ({obj.refugee.get_native_language_display()})"
    refugee_info.short_description = "Refugee"

    def priority_flag(self, obj):
        if obj.priority == 2: 
            return format_html(
                '<div style="background-color: #dc3545; color: white; padding: 5px; text-align: center; border-radius: 4px; font-weight: bold; width: 100px;">{}</div>',
                '🚨 DOCTOR'
            )
        return format_html(
            '<div style="background-color: #28a745; color: white; padding: 5px; text-align: center; border-radius: 4px; width: 100px;">{}</div>',
            '✅ NURSE'
        )
    priority_flag.short_description = "Status"
    
    def save_model(self, request, obj, form, change):
        if not obj.nurse and request.user.is_staff:
            obj.nurse = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if not getattr(instance, 'sender_id', None):
                instance.sender = request.user
            instance.save()
            self.broadcast_message(instance)
        formset.save_m2m()

    def broadcast_message(self, message):
        channel_layer = get_channel_layer()
        if message.session_id:
            room_group_name = f'chat_{message.session_id}'
            message_data = {
                'type': 'chat_message',
                'id': str(message.id),
                'sender_id': message.sender.id,
                'sender_name': message.sender.full_name,
                'text_original': message.text_original if message.text_original else "",
                'text_translated': message.text_translated if message.text_translated else "",
                'timestamp': str(message.timestamp.strftime("%H:%M")),
            }
            if message.image:
                message_data['image_url'] = message.image.url

            async_to_sync(channel_layer.group_send)(
                room_group_name,
                message_data
            )

@admin.register(TranslationCache)
class TranslationCacheAdmin(ModelAdmin):
    list_display = ('source_language', 'target_language', 'source_text', 'created_at')
    readonly_fields = ('source_hash', 'source_text', 'translated_text')