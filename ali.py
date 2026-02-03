@admin.register(ChatSession)
class ChatSessionAdmin(ModelAdmin):
    list_display = ('priority_badge', 'health_id', 'refugee_name', 'last_activity')
    inlines = [MessageInline]
    search_fields = ('refugee__username', 'refugee__full_name')
    list_fullwidth = True
    
    # إخفاء الحقول العامة
    fieldsets = ((None, {'fields': ('refugee', 'nurse', 'priority'), 'classes': ('!hidden',)}),)

    def priority_badge(self, obj):
        return render_to_string('admin/chat/status.html', {'is_urgent': obj.priority == 2})
    priority_badge.short_description = "Status"

    def health_id(self, obj): return obj.refugee.username
    def refugee_name(self, obj): return obj.refugee.full_name

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects: obj.delete()
        for instance in instances:
            if not getattr(instance, 'sender_id', None):
                instance.sender = request.user
            instance.save()
            NotificationService.broadcast_message_update(instance)
        formset.save_m2m()
    
    class Media:
        js = ('js/admin_realtime.js',)