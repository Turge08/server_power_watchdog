from __future__ import annotations

import threading
from collections import deque
from dataclasses import replace
from typing import List, Optional

from app.db import EventRepository
from app.models import AppState, Event


class StateStore:
    def __init__(self, event_repo: EventRepository, max_events: Optional[int] = None):
        self._lock = threading.RLock()
        self._state = AppState()
        self._events = deque(maxlen=max_events or 300)
        self._repo = event_repo

        loaded = self._repo.recent_events(limit=max_events or 300)
        for event in reversed(loaded):
            self._events.appendleft(event)

    def get_state(self) -> AppState:
        with self._lock:
            snapshot = replace(self._state)
            snapshot.current = replace(self._state.current)
            snapshot.events = list(self._events)
            return snapshot

    def update_current(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self._state.current, key, value)

    def add_event(self, level: str, source: str, message: str, ts) -> None:
        event = Event(ts=ts, level=level, source=source, message=message)
        with self._lock:
            self._events.appendleft(event)
        self._repo.add_event(event)

    def recent_events(self) -> List[Event]:
        with self._lock:
            return list(self._events)
