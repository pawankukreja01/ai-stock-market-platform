# Release-candidate backend. No database migrations are run automatically.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt requirements-preview.txt /app/
# CPU PyTorch and FinBERT packages are only needed for the opt-in
# analyze_news_sentiment management command. Excluding them by default
# cuts hundreds of MB from the local preview download on Apple Silicon.
ARG WITH_FINBERT=false
RUN if [ "$WITH_FINBERT" = "true" ]; then \
      pip install --no-cache-dir -r /app/requirements.txt; \
    else \
      pip install --no-cache-dir -r /app/requirements-preview.txt; \
    fi
COPY . /app/
# Build hashed-manifest static assets using production static storage.
# This one-off build key is not a runtime secret or a deployed credential.
RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=ephemeral-build-only-static-assets DJANGO_ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-"]
