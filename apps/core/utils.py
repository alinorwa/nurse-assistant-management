def get_client_ip(request):
    """
    دالة مخصصة لجلب IP المستخدم الحقيقي خلف Docker/Proxy.
    نستخدمها بدلاً من الاعتماد على إعدادات Axes المتغيرة.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # في حال وجود عدة بروكسيات، العنوان الحقيقي هو الأول
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # إذا كان اتصالاً مباشراً
        ip = request.META.get('REMOTE_ADDR')
    return ip