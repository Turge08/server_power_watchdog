from __future__ import annotations

import os
import subprocess
from pathlib import Path


class NUTManager:
    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter

    def _settings(self):
        return self.settings_getter()

    def is_local_mode(self) -> bool:
        s = self._settings()
        return s.nut_enabled and s.nut_connection_mode == "local"

    def _config_dir(self) -> Path:
        return Path(self._settings().nut_config_dir)

    def _write_file(self, path: Path, content: str, mode: int = 0o640) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        try:
            os.chmod(path, mode)
        except OSError:
            pass

    def _render_nut_conf(self) -> str:
        s = self._settings()
        return f"MODE={s.nut_mode}\n"

    def _render_ups_conf(self) -> str:
        s = self._settings()
        return (
            f"[{s.nut_ups_name}]\n"
            f"  driver = {s.nut_driver}\n"
            f"  port = {s.nut_driver_port}\n"
            f"  desc = \"{s.nut_desc}\"\n"
            f"  pollinterval = {s.nut_pollinterval}\n"
            f"  user = root\n"
            f"  group = nut\n"
        )

    def _render_upsd_conf(self) -> str:
        s = self._settings()
        return f"LISTEN {s.nut_listen_host} {s.nut_port}\n"

    def _render_upsd_users(self) -> str:
        s = self._settings()
        blocks = []

        for user in s.nut_users:
            username = str(user.get("username", "")).strip()
            password = str(user.get("password", "")).strip()
            if not username or not password:
                continue

            lines = [
                f"[{username}]",
                f"  password = {password}",
            ]

            actions = str(user.get("actions", "")).strip()
            if actions:
                lines.append(f"  actions = {actions}")

            instcmds = str(user.get("instcmds", "")).strip()
            if instcmds:
                lines.append(f"  instcmds = {instcmds}")

            upsmon = str(user.get("upsmon", "")).strip()
            if upsmon:
                lines.append(f"  upsmon {upsmon}")

            blocks.append("\n".join(lines))

        return ("\n\n".join(blocks) + "\n") if blocks else ""

    def _render_upsmon_conf(self) -> str:
        s = self._settings()
        monitor_user = next(
            (
                u
                for u in s.nut_users
                if str(u.get("username", "")).strip()
                and str(u.get("password", "")).strip()
                and str(u.get("upsmon", "")).strip()
            ),
            None,
        )

        if monitor_user is None:
            raise ValueError("At least one NUT user with an upsmon role is required.")

        username = str(monitor_user["username"]).strip()
        password = str(monitor_user["password"]).strip()
        upsmon_role = str(monitor_user["upsmon"]).strip()
        host = (s.nut_host or "localhost").strip()

        return (
            f"MONITOR {s.nut_ups_name}@{host} 1 {username} {password} {upsmon_role}\n"
            f"MINSUPPLIES 1\n"
            f"POLLFREQ {s.nut_pollinterval}\n"
            f"POLLFREQALERT {s.nut_pollinterval}\n"
            f"HOSTSYNC 15\n"
            f"DEADTIME 15\n"
            f"POWERDOWNFLAG /etc/killpower\n"
        )

    def write_config(self) -> None:
        if not self.is_local_mode():
            return

        config_dir = self._config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)

        self._write_file(config_dir / "nut.conf", self._render_nut_conf(), 0o644)
        self._write_file(config_dir / "ups.conf", self._render_ups_conf(), 0o644)
        self._write_file(config_dir / "upsd.conf", self._render_upsd_conf(), 0o644)
        self._write_file(config_dir / "upsd.users", self._render_upsd_users(), 0o644)
        self._write_file(config_dir / "upsmon.conf", self._render_upsmon_conf(), 0o644)

    def restart(self) -> None:
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
