"""Proxy Collector Pro - Proxy Validation Engine"""

import time
import threading
import requests
import socks
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from config.settings import Settings
from config.constants import ValidationMode, AnonymityLevel
from core.models import Proxy, ValidationResult
from engine.endpoints import EndpointManager
from engine.geoip import GeoIPResolver
from engine.anonymity import AnonymityChecker
from utils.logger import get_logger

logger = get_logger()

class ProxyValidator:
    """Validates proxies with independent protocol testing and evidence-based scoring."""

    def __init__(self):
        self._settings = Settings.load()
        self._endpoint_manager = EndpointManager()
        self._geoip = GeoIPResolver()
        self._anonymity = AnonymityChecker()
        self._session_pool: Dict[str, requests.Session] = {}
        self._pool_lock = threading.Lock()

    def _get_session(self, protocol: str) -> requests.Session:
        with self._pool_lock:
            if protocol not in self._session_pool:
                session = requests.Session()
                session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=self._settings.connection_pool_size,
                    pool_maxsize=self._settings.connection_pool_size,
                    max_retries=0
                )
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                self._session_pool[protocol] = session
            return self._session_pool[protocol]

    def validate(self, proxy: Proxy, protocol: str, endpoint: Optional[str] = None) -> ValidationResult:
        """Validate a single proxy for a specific protocol."""
        start_time = time.time()

        if not endpoint:
            pool = self._endpoint_manager.get_pool(protocol)
            endpoint = pool.get_endpoint()

        proxy_url = f"{protocol}://{proxy.host}:{proxy.port}"

        try:
            if protocol in ("http", "https"):
                success, latency, error = self._validate_http(proxy_url, protocol, endpoint)
            elif protocol == "socks4":
                success, latency, error = self._validate_socks4(proxy.host, proxy.port, endpoint)
            elif protocol == "socks5":
                success, latency, error = self._validate_socks5(proxy.host, proxy.port, endpoint)
            else:
                success, latency, error = False, 0, f"Unknown protocol: {protocol}"

            anonymity = AnonymityLevel.UNCLASSIFIED.value
            if success and self._settings.validation_mode in (ValidationMode.DOUBLE.value, ValidationMode.STABILITY.value):
                anonymity, _ = self._anonymity.check(proxy_url, protocol, self._settings.timeout)

            result = ValidationResult(
                proxy=proxy,
                protocol=protocol,
                success=success,
                latency=latency,
                anonymity=anonymity,
                error=error,
                endpoint_used=endpoint or "",
                timestamp=datetime.now().isoformat()
            )

            if endpoint:
                self._endpoint_manager.get_pool(protocol).report_result(endpoint, success, latency)

            return result

        except Exception as e:
            logger.debug(f"Validation exception for {proxy_url}: {e}", "validator")
            return ValidationResult(
                proxy=proxy,
                protocol=protocol,
                success=False,
                latency=time.time() - start_time,
                error=str(e),
                endpoint_used=endpoint or "",
                timestamp=datetime.now().isoformat()
            )

    def _validate_http(self, proxy_url: str, protocol: str, endpoint: str) -> Tuple[bool, float, str]:
        start = time.time()
        try:
            session = self._get_session(protocol)
            proxies = {protocol: proxy_url}
            resp = session.get(
                endpoint,
                proxies=proxies,
                timeout=self._settings.timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                allow_redirects=False
            )
            latency = time.time() - start

            if resp.status_code == 200:
                return True, latency, ""
            elif resp.status_code in (301, 302, 307, 308):
                return True, latency, f"Redirect {resp.status_code}"
            else:
                return False, latency, f"HTTP {resp.status_code}"

        except requests.exceptions.ProxyError as e:
            return False, time.time() - start, f"Proxy error: {str(e)[:50]}"
        except requests.exceptions.ConnectTimeout:
            return False, time.time() - start, "Connection timeout"
        except requests.exceptions.ReadTimeout:
            return False, time.time() - start, "Read timeout"
        except requests.exceptions.ConnectionError as e:
            return False, time.time() - start, f"Connection error: {str(e)[:50]}"
        except Exception as e:
            return False, time.time() - start, f"Error: {str(e)[:50]}"

    def _validate_socks4(self, host: str, port: int, endpoint: str) -> Tuple[bool, float, str]:
        start = time.time()
        try:
            # Use requests with SOCKS4 proxy for proper HTTP validation
            proxy_url = f"socks4://{host}:{port}"
            proxies = {"http": proxy_url, "https": proxy_url}

            # Use HTTP endpoint for SOCKS4 (more compatible)
            test_endpoint = endpoint
            if endpoint.startswith("https://"):
                # Try to find an HTTP equivalent or use a known HTTP endpoint
                test_endpoint = "http://httpbin.org/ip"

            resp = requests.get(
                test_endpoint,
                proxies=proxies,
                timeout=self._settings.timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                allow_redirects=False
            )
            latency = time.time() - start

            if resp.status_code == 200:
                return True, latency, ""
            elif resp.status_code in (301, 302, 307, 308):
                return True, latency, f"Redirect {resp.status_code}"
            else:
                return False, latency, f"HTTP {resp.status_code}"

        except requests.exceptions.ProxyError as e:
            return False, time.time() - start, f"Proxy error: {str(e)[:50]}"
        except requests.exceptions.ConnectTimeout:
            return False, time.time() - start, "Connection timeout"
        except requests.exceptions.ReadTimeout:
            return False, time.time() - start, "Read timeout"
        except requests.exceptions.ConnectionError as e:
            return False, time.time() - start, f"Connection error: {str(e)[:50]}"
        except Exception as e:
            return False, time.time() - start, f"SOCKS4 error: {str(e)[:50]}"

    def _validate_socks5(self, host: str, port: int, endpoint: str) -> Tuple[bool, float, str]:
        start = time.time()
        try:
            # Use requests with SOCKS5 proxy for proper HTTP validation
            proxy_url = f"socks5://{host}:{port}"
            proxies = {"http": proxy_url, "https": proxy_url}

            # Use HTTP endpoint for SOCKS5 (more compatible)
            test_endpoint = endpoint
            if endpoint.startswith("https://"):
                test_endpoint = "http://httpbin.org/ip"

            resp = requests.get(
                test_endpoint,
                proxies=proxies,
                timeout=self._settings.timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                allow_redirects=False
            )
            latency = time.time() - start

            if resp.status_code == 200:
                return True, latency, ""
            elif resp.status_code in (301, 302, 307, 308):
                return True, latency, f"Redirect {resp.status_code}"
            else:
                return False, latency, f"HTTP {resp.status_code}"

        except requests.exceptions.ProxyError as e:
            return False, time.time() - start, f"Proxy error: {str(e)[:50]}"
        except requests.exceptions.ConnectTimeout:
            return False, time.time() - start, "Connection timeout"
        except requests.exceptions.ReadTimeout:
            return False, time.time() - start, "Read timeout"
        except requests.exceptions.ConnectionError as e:
            return False, time.time() - start, f"Connection error: {str(e)[:50]}"
        except Exception as e:
            return False, time.time() - start, f"SOCKS5 error: {str(e)[:50]}"

    def validate_all_protocols(self, proxy: Proxy) -> Dict[str, ValidationResult]:
        """Validate proxy against all protocols independently."""
        results = {}
        for protocol in ["http", "https", "socks4", "socks5"]:
            result = self.validate(proxy, protocol)
            results[protocol] = result
        return results

    def close(self) -> None:
        for session in self._session_pool.values():
            session.close()
        self._session_pool.clear()
