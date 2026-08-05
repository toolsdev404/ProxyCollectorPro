"""Proxy Collector Pro - Endpoint Pool Management"""

import random
import threading
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import urllib.request
import ssl
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger()

class EndpointPool:
    """Manages validation endpoints with automatic failover and health tracking."""

    def __init__(self, protocol: str):
        self.protocol = protocol
        self._endpoints: List[str] = []
        self._health: Dict[str, Dict[str, Any]] = {}
        self._current_index = 0
        self._lock = threading.Lock()
        self._settings = Settings.load()
        self._load_endpoints()

    def _load_endpoints(self) -> None:
        if self.protocol == "http":
            self._endpoints = self._settings.http_endpoints.copy()
        elif self.protocol == "https":
            self._endpoints = self._settings.https_endpoints.copy()
        else:
            # SOCKS protocols use HTTP/HTTPS endpoints for validation
            self._endpoints = self._settings.https_endpoints.copy()

        for ep in self._endpoints:
            self._health[ep] = {
                "successes": 0,
                "failures": 0,
                "last_used": 0,
                "avg_latency": 0.0,
                "healthy": True
            }

    def get_endpoint(self) -> Optional[str]:
        with self._lock:
            healthy = [ep for ep in self._endpoints if self._health[ep]["healthy"]]
            if not healthy:
                # Reset all if none healthy
                for ep in self._endpoints:
                    self._health[ep]["healthy"] = True
                healthy = self._endpoints.copy()

            # True round-robin: cycle through endpoints
            if not hasattr(self, '_rr_index'):
                self._rr_index = 0

            endpoint = healthy[self._rr_index % len(healthy)]
            self._rr_index = (self._rr_index + 1) % len(healthy)
            self._health[endpoint]["last_used"] = time.time()
            return endpoint

    def report_result(self, endpoint: str, success: bool, latency: float) -> None:
        with self._lock:
            if endpoint not in self._health:
                return

            h = self._health[endpoint]
            if success:
                h["successes"] += 1
                if h["avg_latency"] == 0:
                    h["avg_latency"] = latency
                else:
                    h["avg_latency"] = h["avg_latency"] * 0.7 + latency * 0.3
            else:
                h["failures"] += 1

            total = h["successes"] + h["failures"]
            if total >= 5:
                h["healthy"] = (h["successes"] / total) > 0.3

    def get_all_endpoints(self) -> List[str]:
        return self._endpoints.copy()

    def add_endpoint(self, endpoint: str) -> None:
        with self._lock:
            if endpoint not in self._endpoints:
                self._endpoints.append(endpoint)
                self._health[endpoint] = {
                    "successes": 0, "failures": 0, "last_used": 0,
                    "avg_latency": 0.0, "healthy": True
                }

    def remove_endpoint(self, endpoint: str) -> None:
        with self._lock:
            if endpoint in self._endpoints:
                self._endpoints.remove(endpoint)
                self._health.pop(endpoint, None)

class EndpointManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pools = {}
        return cls._instance

    def get_pool(self, protocol: str) -> EndpointPool:
        if protocol not in self._pools:
            self._pools[protocol] = EndpointPool(protocol)
        return self._pools[protocol]

    def refresh_all(self) -> None:
        for pool in self._pools.values():
            pool._load_endpoints()
