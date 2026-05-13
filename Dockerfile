FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpq-dev \
        fonts-thai-tlwg \
        fonts-noto-cjk \
        curl \
        ca-certificates \
        tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Bangkok /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /bin/bash thaibill

WORKDIR /app

COPY --chown=thaibill:thaibill requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

COPY --chown=thaibill:thaibill . .

RUN mkdir -p instance app/static/uploads/logos app/static/uploads/signatures app/static/uploads/attachments logs && \
    chown -R thaibill:thaibill instance app/static/uploads logs

USER thaibill

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/login || exit 1

ENV FLASK_ENV=production \
    SECRET_KEY=change-me-in-production \
    PYTHONPATH=/app

CMD ["gunicorn", "--workers=2", "--threads=4", "--bind=0.0.0.0:8000", \
     "--access-logfile=-", "--error-logfile=-", "--timeout=120", "wsgi:app"]
