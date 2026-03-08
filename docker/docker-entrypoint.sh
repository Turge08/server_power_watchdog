#!/bin/bash
set -e

echo "----------------------------------------"
echo " Server Power Watchdog Docker Container "
echo "----------------------------------------"

mkdir -p /config/data /config/logs /config/nut /var/run/nut /run/nut
chown nut:nut /var/run/nut /run/nut || true
chmod 775 /var/run/nut /run/nut || true

if [ ! -L "/app/data" ]; then
  rm -rf /app/data 2>/dev/null || true
  ln -sf /config/data /app/data
fi

if [ ! -f "/config/data/settings.json" ]; then
  echo "No settings.json found in /config/data."
  echo "The app will create one on first startup."
fi

echo "Configuration directory: /config"
echo "Data directory: /config/data"
echo "NUT config directory: /etc/nut"
echo "Web Port: ${WEB_PORT:-8080}"
echo "Timezone: ${TZ:-America/Toronto}"
echo ""

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
