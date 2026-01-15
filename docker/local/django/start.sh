#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# تطبيق التغييرات على قاعدة البيانات (SQLite)
python manage.py migrate

# تجميع الملفات الاستاتيكية
python manage.py collectstatic --no-input

# تشغيل سيرفر Daphne (لدعم الشات والترجمة)
echo "Starting Daphne Server..."
daphne -b 0.0.0.0 -p 8000 config.asgi:application