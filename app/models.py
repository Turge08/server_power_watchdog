from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_localtime(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def format_localtime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %I:%M:%S %p %Z") -> str:
    local_dt = to_localtime(dt)
    if local_dt is None:
        return "--"
    return local_dt.strftime(fmt)


@dataclass
class CurrentState:
    ups_usb_present: Optional[bool] = None
    nut_healthy: Optional[bool] = None
    ups_status: str = "unknown"
    ups_battery_percent: Optional[float] = None
    ups_runtime_seconds: Optional[int] = None
    server_powered_on: Optional[bool] = None
    nanokvm_authenticated: Optional[bool] = None
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None
    last_power_on_attempt: Optional[datetime] = None
    last_error: Optional[str] = None
    last_action: Optional[str] = None


@dataclass
class Event:
    ts: datetime
    level: str
    source: str
    message: str


@dataclass
class AppState:
    current: CurrentState = field(default_factory=CurrentState)
    events: List[Event] = field(default_factory=list)
