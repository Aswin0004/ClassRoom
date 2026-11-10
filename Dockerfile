FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 classroom

COPY . .

RUN DJANGO_DEBUG=True \
    DJANGO_SECRET_KEY=BUILD_ONLY_NOT_FOR_RUNTIME_12345678901234567890 \
    python manage.py collectstatic --noinput

USER classroom

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]