FROM python:3.13-slim-bullseye

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

# التعديل هنا: أضفنا netcat-openbsd للقائمة
RUN apt-get update \
  && apt-get install -y build-essential libpq-dev gettext netcat-openbsd \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY ./docker/local/django/entrypoint.sh /entrypoint.sh
# إصلاح نهايات الأسطر (للويندوز)
RUN sed -i 's/\r$//g' /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./docker/local/django/start.sh /start.sh
# إصلاح نهايات الأسطر (للويندوز)
RUN sed -i 's/\r$//g' /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/entrypoint.sh"]