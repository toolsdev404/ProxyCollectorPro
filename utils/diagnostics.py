"""Proxy Collector Pro - System Diagnostics"""

import os
import sys
import socket
import sqlite3
import importlib
import subprocess
from typing import Dict, Any, List, Tuple
from config.constants import DB_FILE, EXPORTS_DIR
from config.settings import Settings

class DiagnosticResult:
    def __init__(self, name: str, status: str, message: str = "", details: Dict[str, Any] = None):
        self.name = name
        self.status = status  # "ok", "warning", "error"
        self.message = message
        self.details = details or {}

class Diagnostics:
    @staticmethod
    def run_all() -> List[DiagnosticResult]:
        results = []
        results.append(Diagnostics.check_internet())
        results.append(Diagnostics.check_dns())
        results.append(Diagnostics.check_sqlite())
        results.append(Diagnostics.check_socks())
        results.append(Diagnostics.check_export_folder())
        results.append(Diagnostics.check_http_endpoints())
        results.append(Diagnostics.check_https_endpoints())
        results.append(Diagnostics.check_geoip())
        results.append(Diagnostics.check_dependencies())
        return results

    @staticmethod
    def check_internet() -> DiagnosticResult:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return DiagnosticResult("Internet", "ok", "Internet connection is available")
        except OSError:
            return DiagnosticResult("Internet", "error", "No internet connection detected")

    @staticmethod
    def check_dns() -> DiagnosticResult:
        try:
            socket.gethostbyname("google.com")
            return DiagnosticResult("DNS", "ok", "DNS resolution is working")
        except socket.gaierror:
            return DiagnosticResult("DNS", "error", "DNS resolution failed")

    @staticmethod
    def check_sqlite() -> DiagnosticResult:
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.close()

            db_exists = os.path.exists(DB_FILE)
            size = os.path.getsize(DB_FILE) if db_exists else 0

            return DiagnosticResult("SQLite", "ok", 
                f"SQLite OK (WAL supported). DB: {'Exists' if db_exists else 'Not created'} ({size} bytes)")
        except Exception as e:
            return DiagnosticResult("SQLite", "error", f"SQLite error: {str(e)}")

    @staticmethod
    def check_socks() -> DiagnosticResult:
        try:
            import socks
            return DiagnosticResult("SOCKS", "ok", "PySocks is available")
        except ImportError:
            return DiagnosticResult("SOCKS", "warning", "PySocks not installed. SOCKS validation will be limited.")

    @staticmethod
    def check_export_folder() -> DiagnosticResult:
        try:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            test_file = os.path.join(EXPORTS_DIR, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return DiagnosticResult("Export Folder", "ok", f"Export folder writable: {EXPORTS_DIR}")
        except Exception as e:
            return DiagnosticResult("Export Folder", "error", f"Export folder error: {str(e)}")

    @staticmethod
    def check_http_endpoints() -> DiagnosticResult:
        import urllib.request
        settings = Settings.load()
        endpoints = settings.http_endpoints[:3]
        working = 0
        details = {}

        for ep in endpoints:
            try:
                req = urllib.request.Request(ep, method="HEAD", headers={"User-Agent": "ProxyCollector/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    working += 1
                    details[ep] = f"HTTP {resp.status}"
            except Exception as e:
                details[ep] = f"Failed: {str(e)[:50]}"

        status = "ok" if working > 0 else "warning"
        return DiagnosticResult("HTTP Endpoints", status, 
            f"{working}/{len(endpoints)} HTTP endpoints reachable", details)

    @staticmethod
    def check_https_endpoints() -> DiagnosticResult:
        import urllib.request
        import ssl
        settings = Settings.load()
        endpoints = settings.https_endpoints[:3]
        working = 0
        details = {}

        ctx = ssl.create_default_context()
        for ep in endpoints:
            try:
                req = urllib.request.Request(ep, method="HEAD", headers={"User-Agent": "ProxyCollector/1.0"})
                with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                    working += 1
                    details[ep] = f"HTTP {resp.status}"
            except Exception as e:
                details[ep] = f"Failed: {str(e)[:50]}"

        status = "ok" if working > 0 else "warning"
        return DiagnosticResult("HTTPS Endpoints", status, 
            f"{working}/{len(endpoints)} HTTPS endpoints reachable", details)

    @staticmethod
    def check_geoip() -> DiagnosticResult:
        try:
            import urllib.request
            req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "ProxyCollector/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                return DiagnosticResult("GeoIP", "ok", "GeoIP service reachable")
        except Exception as e:
            return DiagnosticResult("GeoIP", "warning", f"GeoIP check failed (optional): {str(e)[:50]}")

    @staticmethod
    def check_dependencies() -> DiagnosticResult:
        required = ["customtkinter", "requests", "socks", "sqlite3"]
        missing = []
        details = {}

        for pkg in required:
            try:
                if pkg == "sqlite3":
                    import sqlite3
                    details[pkg] = sqlite3.sqlite_version
                elif pkg == "socks":
                    import socks
                    details[pkg] = "installed"
                else:
                    mod = importlib.import_module(pkg)
                    ver = getattr(mod, "__version__", "installed")
                    details[pkg] = ver
            except ImportError:
                missing.append(pkg)
                details[pkg] = "missing"

        if missing:
            return DiagnosticResult("Dependencies", "error", 
                f"Missing: {', '.join(missing)}", details)
        return DiagnosticResult("Dependencies", "ok", "All dependencies available", details)
