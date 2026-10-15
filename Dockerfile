FROM node:24-slim AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build:css


FROM python:3.14-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"
RUN python -m venv /opt/venv \
 && useradd --create-home --uid 1000 wagtail
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
WORKDIR /app
RUN chown wagtail:wagtail /app


FROM base AS dev
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install -r /tmp/requirements-dev.txt
ENV DJANGO_SETTINGS_MODULE=sitehealth.settings.dev
USER wagtail
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS production
ENV DJANGO_SETTINGS_MODULE=sitehealth.settings.production \
    WEB_CONCURRENCY=3
COPY --chown=wagtail:wagtail . .
COPY --from=assets --chown=wagtail:wagtail /app/sitehealth/static/css/main.css sitehealth/static/css/main.css
USER wagtail
RUN mkdir -p media \
 && SECRET_KEY=collectstatic-only \
    DATABASE_URL=postgres://collectstatic/unused \
    ALLOWED_HOSTS=localhost \
    CSRF_TRUSTED_ORIGINS=https://localhost \
    WAGTAILADMIN_BASE_URL=https://localhost \
    python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "sitehealth.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-"]
