"""Proxy Collector Pro - GeoIP Resolution (Optional)"""

import json
import socket
import urllib.request
from typing import Dict, Optional, Any
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger()

class GeoIPResolver:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._settings = Settings.load()

    def resolve(self, ip: str) -> Optional[Dict[str, str]]:
        if not self._settings.geoip_enabled:
            return None

        if ip in self._cache:
            return self._cache[ip]

        try:
            # Try ipapi.co first
            data = self._resolve_ipapi(ip)
            if data:
                self._cache[ip] = data
                return data
        except Exception as e:
            logger.debug(f"GeoIP failed for {ip}: {e}", "geoip")

        return None

    def _resolve_ipapi(self, ip: str) -> Optional[Dict[str, str]]:
        try:
            url = f"https://ipapi.co/{ip}/json/"
            req = urllib.request.Request(url, headers={"User-Agent": "ProxyCollector/1.0"})
            with urllib.request.urlopen(req, timeout=self._settings.geoip_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                if "error" in data:
                    return None

                return {
                    "country": data.get("country_name", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("org", ""),
                    "asn": str(data.get("asn", "")),
                    "organization": data.get("org", ""),
                }
        except Exception:
            return None

    def clear_cache(self) -> None:
        self._cache.clear()
