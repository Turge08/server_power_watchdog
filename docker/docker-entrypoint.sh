#!/bin/sh
set -e

mkdir -p /config/data /config/data/nut /config/logs /var/run/nut /run/nut
chown nut:nut /var/run/nut /run/nut || true
chmod 775 /var/run/nut /run/nut || true

if [ ! -L "/app/data" ]; then
  rm -rf /app/data 2>/dev/null || true
  ln -sf /config/data /app/data
fi

rm -rf /etc/nut
ln -sf /config/data/nut /etc/nut

if [ ! -f "/config/data/settings.json" ]; then
  echo "No settings.json found in /config/data."
  echo "The app will create one on first startup."
fi

NUT_MODE="$(python - <<'PY'
from app.config import AppSettings
from app.settings_store import SettingsStore

store = SettingsStore(AppSettings.default().settings_path)
settings = store.get()
print(settings.nut_connection_mode)
PY
)"

if [ "${NUT_MODE}" = "local" ]; then
  UPS_NAME="$(python - <<'PY'
from app.config import AppSettings
from app.settings_store import SettingsStore

store = SettingsStore(AppSettings.default().settings_path)
settings = store.get()
print(settings.nut_ups_name)
PY
)"

  python - <<'PY'
from app.config import AppSettings
from app.services.nut_manager import NUTManager
from app.settings_store import SettingsStore

store = SettingsStore(AppSettings.default().settings_path)
NUTManager(store.get).write_config()
PY

  cat >/etc/supervisor/conf.d/supervisord.conf <<EOF
[supervisord]
nodaemon=true
user=root
logfile=/dev/stdout
logfile_maxbytes=0
pidfile=/tmp/supervisord.pid

[unix_http_server]
file=/tmp/supervisor.sock
chmod=0700

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:nut-driver]
command=/lib/nut/usbhid-ups -a ${UPS_NAME} -F
priority=10
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:nut-socket-fix]
command=/bin/sh -c 'while true; do if [ -S /run/nut/usbhid-ups-${UPS_NAME} ]; then chgrp nut /run/nut/usbhid-ups-${UPS_NAME} 2>/dev/null || true; chmod 660 /run/nut/usbhid-ups-${UPS_NAME} 2>/dev/null || true; fi; sleep 1; done'
priority=15
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:upsd]
command=/bin/sh -c 'sleep 5; exec /usr/sbin/upsd -F'
priority=20
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:web]
command=/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
directory=/app
priority=30
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF
else
  cat >/etc/supervisor/conf.d/supervisord.conf <<'EOF'
[supervisord]
nodaemon=true
user=root
logfile=/dev/stdout
logfile_maxbytes=0
pidfile=/tmp/supervisord.pid

[unix_http_server]
file=/tmp/supervisor.sock
chmod=0700

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:web]
command=/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
directory=/app
priority=30
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF
fi

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
