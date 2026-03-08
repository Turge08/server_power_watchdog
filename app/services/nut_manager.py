from __future__ import annotations

import subprocess


class NUTManager:
    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter

    def _settings(self):
        return self.settings_getter()

    def is_local_mode(self) -> bool:
        s = self._settings()
        return s.nut_enabled and s.nut_connection_mode == "local"

    def write_config(self) -> None:
        # Intentionally disabled for now.
        # Local NUT config is managed outside the app.
        return

    def restart(self) -> None:
        # Intentionally disabled for now.
        # Local NUT process management is handled outside the app.
        return

    def test(self) -> str:
        s = self._settings()

        if not s.nut_enabled or s.nut_connection_mode == "disabled":
            return "NUT is disabled."

        host = (s.nut_host or "localhost").strip()
        target = s.nut_target_override.strip() if s.nut_target_override else f"{s.nut_ups_name}@{host}"

        proc = subprocess.run(
            ["upsc", target],
            capture_output=True,
            text=True,
        )
        output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        return output or "No output returned by upsc."
