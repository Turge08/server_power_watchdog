from __future__ import annotations

import json
import os
from dataclasses import fields
from pathlib import Path
from typing import Any

from app.config import AppSettings


SECRET_FIELDS = {
    "nanokvm_password",
    "mqtt_password",
    "telegram_token",
    "telegram_chat_id",
}

BOOL_FIELDS = {
    "debug",
    "allow_power_control",
    "nut_use_subprocess",
    "usb_detection_enabled",
    "telegram_notify_ups_status_changes",
}

INT_FIELDS = {
    "poll_interval",
    "power_on_cooldown",
    "nut_port",
    "nanokvm_timeout_seconds",
    "nanokvm_power_duration_ms",
    "mqtt_port",
    "max_events_in_memory",
}


class SettingsStore:
    def __init__(self, path: str):
        self.path = path
        self._settings = self.load()

    def _defaults_dict(self) -> dict[str, Any]:
        return AppSettings.default().to_dict()

    def _coerce_value(self, key: str, value: Any) -> Any:
        if key in BOOL_FIELDS:
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}

        if key in INT_FIELDS:
            return int(value)

        return value

    def load(self) -> AppSettings:
        defaults = self._defaults_dict()

        if not Path(self.path).exists():
            settings = AppSettings.default()
            self.save(settings)
            return settings

        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        merged = defaults.copy()
        for key, value in raw.items():
            if key in merged:
                merged[key] = self._coerce_value(key, value)

        return AppSettings(**merged)

    def save(self, settings: AppSettings) -> None:
        AppSettings.ensure_parent_dirs(self.path)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)
            f.write("\n")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        self._settings = settings

    def get(self) -> AppSettings:
        return self._settings

    def update_from_form(self, form_data: dict[str, Any]) -> AppSettings:
        current = self.get().to_dict()
        valid_fields = {f.name for f in fields(AppSettings)}

        for key in valid_fields:
            if key in BOOL_FIELDS:
                current[key] = key in form_data
                continue

            if key not in form_data:
                continue

            value = form_data[key]

            if key in SECRET_FIELDS:
                value = str(value)
                if value.strip() == "":
                    continue

            current[key] = self._coerce_value(key, value)

        updated = AppSettings(**current)
        self.save(updated)
        return updated

    def masked_dict(self) -> dict[str, Any]:
        data = self.get().to_dict()
        for key in SECRET_FIELDS:
            if data.get(key):
                data[key] = "********"
        return data
