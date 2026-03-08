#!/bin/bash
set -e

echo "----------------------------------------"
echo " Server Power Watchdog Docker Container "
echo "----------------------------------------"

mkdir -p /config/data /config/logs /config/nut /var/run/nut

if [ ! -L "/app/data" ]; then
  rm -rf /app/data 2>/dev/null || true
  ln -sf /config/data /app/data
fi

if [ ! -L "/etc/nut" ]; then
  :
fi

# Persist settings.json
if [ ! -f "/config/data/settings.json" ] && [ -f "/app/data/settings.json" ]; then
  cp /app/data/settings.json /config/data/settings.json
fi

echo "Configuration directory: /config"
echo "Data directory: /config/data"
echo "NUT config directory: /etc/nut"
echo "Web Port: ${WEB_PORT:-8080}"
echo "Timezone: ${TZ:-America/Toronto}"
echo ""

echo "Starting NUT + Web UI..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
