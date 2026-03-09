FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nut \
    nut-server \
    nut-client \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh && \
    mkdir -p /config /config/data /config/data/nut /config/logs /etc/nut /var/run/nut /run/nut && \
    chmod -R 777 /config /var/run/nut /run/nut

EXPOSE 8000
EXPOSE 3493

ENTRYPOINT ["/docker-entrypoint.sh"]
