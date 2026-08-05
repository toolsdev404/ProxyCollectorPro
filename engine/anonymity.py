"""Proxy Collector Pro - Anonymity Level Detection"""

import re
import json
import urllib.request
from typing import Dict, Optional, Tuple, Any
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger()

class AnonymityChecker:
    """Evidence-based anonymity detection."""

    HEADERS_TO_CHECK = [
        "HTTP_X_FORWARDED_FOR",
        "HTTP_X_FORWARDED",
        "HTTP_X_CLUSTER_CLIENT_IP",
        "HTTP_FORWARDED_FOR",
        "HTTP_FORWARDED",
        "HTTP_VIA",
        "HTTP_X_REAL_IP",
        "HTTP_CLIENT_IP",
        "HTTP_PROXY_CONNECTION",
        "REMOTE_ADDR",
    ]

    def __init__(self):
        self._settings = Settings.load()

    def check(self, proxy_url: str, protocol: str, timeout: int = 10) -> Tuple[str, Dict[str, Any]]:
        """
        Returns: (anonymity_level, evidence_dict)
        Levels: elite, anonymous, transparent, unclassified
        """
        try:
            if protocol in ("socks4", "socks5"):
                return self._check_socks(proxy_url, timeout)
            else:
                return self._check_http(proxy_url, protocol, timeout)
        except Exception as e:
            logger.debug(f"Anonymity check failed for {proxy_url}: {e}", "anonymity")
            return "unclassified", {"error": str(e)}

    def _check_http(self, proxy_url: str, protocol: str, timeout: int) -> Tuple[str, Dict[str, Any]]:
        import requests

        evidence = {
            "headers_leaked": [],
            "real_ip_exposed": False,
            "proxy_detected": False,
        }

        try:
            proxies = {protocol: proxy_url}
            resp = requests.get(
                "https://httpbin.org/get",
                proxies=proxies,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            data = resp.json()

            origin = data.get("origin", "")
            headers = data.get("headers", {})

            # Check for proxy-related headers
            proxy_headers = ["Via", "X-Proxy-Id", "Proxy-Connection", "X-Forwarded-For"]
            for h in proxy_headers:
                if h in headers:
                    evidence["headers_leaked"].append(h)
                    evidence["proxy_detected"] = True

            # Check if real IP is exposed
            if origin and "," in origin:
                evidence["real_ip_exposed"] = True

            # Determine level
            if evidence["proxy_detected"] or evidence["real_ip_exposed"]:
                if evidence["real_ip_exposed"]:
                    return "transparent", evidence
                return "anonymous", evidence

            if not evidence["headers_leaked"] and not evidence["real_ip_exposed"]:
                return "elite", evidence

            return "anonymous", evidence

        except Exception as e:
            return "unclassified", {"error": str(e)}

    def _check_socks(self, proxy_url: str, timeout: int) -> Tuple[str, Dict[str, Any]]:
        import socks
        import socket

        evidence = {"type": "socks"}

        try:
            # SOCKS proxies generally don't leak headers
            # We can only verify they work, assume anonymous at minimum
            old_socket = socket.socket

            parsed = proxy_url.replace("socks4://", "").replace("socks5://", "").split(":")
            host, port = parsed[0], int(parsed[1])

            if "socks5" in proxy_url:
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, host, port)
            else:
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS4, host, port)

            s.settimeout(timeout)
            s.connect(("httpbin.org", 80))
            s.close()

            # Without header inspection, we mark as anonymous (cannot confirm elite)
            return "anonymous", evidence

        except Exception as e:
            return "unclassified", {"error": str(e)}
        finally:
            socket.socket = old_socket if 'old_socket' in dir() else socket.socket
