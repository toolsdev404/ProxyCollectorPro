"""Proxy Collector Pro - Fair Round-Robin Scheduler"""

import queue
import threading
import time
from typing import List, Dict, Optional, Set, Any
from collections import deque
from config.settings import Settings
from config.constants import Protocol
from core.models import Proxy, ValidationJob
from utils.logger import get_logger

logger = get_logger()

class FairScheduler:
    """Fair round-robin scheduler preventing protocol starvation."""

    def __init__(self):
        self._settings = Settings.load()
        self._queues: Dict[str, deque] = {
            Protocol.HTTP.value: deque(),
            Protocol.HTTPS.value: deque(),
            Protocol.SOCKS4.value: deque(),
            Protocol.SOCKS5.value: deque(),
        }
        self._lock = threading.Lock()
        self._protocols = list(self._queues.keys())
        self._current_index = 0
        self._stopped = False
        self._paused = False
        self._targets: Dict[str, int] = {
            Protocol.HTTP.value: self._settings.target_http,
            Protocol.HTTPS.value: self._settings.target_https,
            Protocol.SOCKS4.value: self._settings.target_socks4,
            Protocol.SOCKS5.value: self._settings.target_socks5,
        }
        self._current_counts: Dict[str, int] = {
            Protocol.HTTP.value: 0,
            Protocol.HTTPS.value: 0,
            Protocol.SOCKS4.value: 0,
            Protocol.SOCKS5.value: 0,
        }
        self._seen: Set[str] = set()

    def set_targets(self, http: int, https: int, socks4: int, socks5: int, total: int) -> None:
        with self._lock:
            self._targets[Protocol.HTTP.value] = http
            self._targets[Protocol.HTTPS.value] = https
            self._targets[Protocol.SOCKS4.value] = socks4
            self._targets[Protocol.SOCKS5.value] = socks5
            self._total_target = total

    def add_job(self, job: ValidationJob) -> bool:
        with self._lock:
            if self._stopped:
                return False

            key = f"{job.proxy.host}:{job.proxy.port}:{job.protocol}"
            if key in self._seen:
                return False
            self._seen.add(key)

            protocol = job.protocol
            if protocol in self._queues:
                self._queues[protocol].append(job)
                return True
            return False

    def add_jobs(self, jobs: List[ValidationJob]) -> int:
        count = 0
        for job in jobs:
            if self.add_job(job):
                count += 1
        return count

    def get_job(self) -> Optional[ValidationJob]:
        with self._lock:
            if self._stopped or self._paused:
                return None

            # Round-robin across protocols
            for _ in range(len(self._protocols)):
                protocol = self._protocols[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._protocols)

                # Skip if target reached
                if self._current_counts.get(protocol, 0) >= self._targets.get(protocol, 0):
                    continue

                if self._queues[protocol]:
                    job = self._queues[protocol].popleft()
                    return job

            return None

    def mark_success(self, protocol: str) -> None:
        with self._lock:
            self._current_counts[protocol] = self._current_counts.get(protocol, 0) + 1

    def is_target_reached(self, protocol: str) -> bool:
        with self._lock:
            return self._current_counts.get(protocol, 0) >= self._targets.get(protocol, 0)

    def any_target_reached(self) -> Optional[str]:
        with self._lock:
            for protocol in self._protocols:
                if self._current_counts.get(protocol, 0) >= self._targets.get(protocol, 0):
                    return protocol
            return None

    def all_targets_reached(self) -> bool:
        with self._lock:
            for protocol in self._protocols:
                if self._current_counts.get(protocol, 0) < self._targets.get(protocol, 0):
                    return False
            return True

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "queues": {p: len(q) for p, q in self._queues.items()},
                "targets": self._targets.copy(),
                "current": self._current_counts.copy(),
                "total_seen": len(self._seen),
            }

    def reset(self) -> None:
        with self._lock:
            for q in self._queues.values():
                q.clear()
            self._seen.clear()
            self._current_index = 0
            for p in self._protocols:
                self._current_counts[p] = 0

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def stop(self) -> None:
        with self._lock:
            self._stopped = True

    def is_empty(self) -> bool:
        with self._lock:
            return all(len(q) == 0 for q in self._queues.values())
