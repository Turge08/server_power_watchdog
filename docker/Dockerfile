FROM python:3.11-slim

LABEL maintainer="Steve Turgeon"
LABEL org.opencontainers.image.title="Server Power Watchdog"
LABEL org.opencontainers.image.description="UPS, NanoKVM, MQTT, and web UI watchdog"
LABEL org.opencontainers.image.vendor="Steve Turgeon"

ARG GIT_COMMIT=unknown
ARG IMAGE_TAG=latest

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Toronto \
    WEB_PORT=8080 \
    GIT_COMMIT=$GIT_COMMIT \
    IMAGE_TAG=$IMAGE_TAG

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    tzdata \
    curl \
    openssl \
    usbutils \
    nut \
    nut-client \
    nut-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/nut/ /etc/nut/

RUN chmod +x /docker-entrypoint.sh && \
    mkdir -p /config /config/data /config/logs /config/nut /var/run/nut && \
    chmod -R 777 /config /var/run/nut

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${WEB_PORT}/ || exit 1

EXPOSE 8080 3493

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/docker-entrypoint.sh"]
