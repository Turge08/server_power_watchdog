from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


def default_nut_users() -> list[dict[str, str]]:
    return [
        {
            "username": "admin",
            "password": "changeme",
            "actions": "SET",
            "instcmds": "ALL",
            "upsmon": "",
        },
        {
            "username": "monuser",
            "password": "changeme",
            "actions": "",
            "instcmds": "",
            "upsmon": "master",
        },
    ]


@dataclass
class AppSettings:
    app_name: str = "Server Power Watchdog"
    debug: bool = False
    poll_interval: int = 10
    power_on_cooldown: int = 300
    sqlite_path: str = "./data/watchdog.db"
    settings_path: str = "./data/settings.json"
    max_events_in_memory: int = 300

    allow_power_control: bool = False

    nut_enabled: bool = True
    nut_connection_mode: str = "local"   # disabled | local | remote
    nut_mode: str = "netserver"
    nut_config_dir: str = "/etc/nut"
    nut_listen_host: str = "0.0.0.0"
    nut_port: int = 3493
    nut_host: str = "localhost"
    nut_target_override: str = ""
    nut_use_subprocess: bool = True

    nut_ups_name: str = "ups"
    nut_driver: str = "usbhid-ups"
    nut_driver_port: str = "auto"
    nut_desc: str = "UPS"
    nut_pollinterval: int = 5
    nut_users: list[dict[str, str]] = field(default_factory=default_nut_users)

    ups_usb_id: str = "051d:"
    usb_detection_enabled: bool = True
    telegram_notify_ups_status_changes: bool = True

    nanokvm_host: str = "127.0.0.1"
    nanokvm_username: str = "admin"
    nanokvm_password: str = ""
    nanokvm_scheme: str = "http"
    nanokvm_timeout_seconds: int = 10
    nanokvm_power_duration_ms: int = 800

    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_user: str = ""
    mqtt_password: str = ""
    mqtt_base_topic: str = "server_power_watchdog"

    telegram_token: str = ""
    telegram_chat_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def default(cls) -> "AppSettings":
        return cls()

    @classmethod
    def ensure_parent_dirs(cls, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
