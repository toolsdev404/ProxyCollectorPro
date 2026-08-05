"""Proxy Collector Pro - Thread-Safe Event System"""

import queue
import threading
from typing import Callable, Any, Dict, List
from dataclasses import dataclass
from enum import Enum, auto

class EventType(Enum):
    PROXY_FOUND = auto()
    PROXY_VALIDATED = auto()
    PROXY_DEAD = auto()
    COLLECTION_STARTED = auto()
    COLLECTION_PAUSED = auto()
    COLLECTION_RESUMED = auto()
    COLLECTION_STOPPED = auto()
    COLLECTION_COMPLETED = auto()
    SOURCE_ADDED = auto()
    SOURCE_UPDATED = auto()
    SOURCE_REMOVED = auto()
    SOURCE_TESTED = auto()
    EXPORT_STARTED = auto()
    EXPORT_COMPLETED = auto()
    SETTINGS_CHANGED = auto()
    LOG_ENTRY = auto()
    STATS_UPDATE = auto()
    TARGET_REACHED = auto()
    ERROR = auto()

@dataclass
class AppEvent:
    event_type: EventType
    data: Any = None
    timestamp: str = ""

class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        self._running = True

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                except ValueError:
                    pass

    def publish(self, event: AppEvent) -> None:
        with self._lock:
            subscribers = self._subscribers.get(event.event_type, []).copy()
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                pass

    def publish_async(self, event: AppEvent) -> None:
        self._queue.put(event)

    def process_queue(self) -> None:
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                self.publish(event)
            except queue.Empty:
                break

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

# Global event bus instance
event_bus = EventBus()
