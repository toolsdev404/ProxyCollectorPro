"""Proxy Collector Pro - Persistent Logging System"""

import os
import sys
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from config.constants import LOGS_DIR, LogLevel
from core.events import event_bus, EventType, AppEvent
from core.models import LogEntry

class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[37m",
        "SUCCESS": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)

class AppLogger:
    _instance: Optional["AppLogger"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = LOGS_DIR, max_size_mb: int = 10, backup_count: int = 5):
        if self._initialized:
            return
        self._initialized = True

        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        self.logger = logging.getLogger("ProxyCollectorPro")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.DEBUG)
        console_fmt = ColoredFormatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%H:%M:%S")
        console.setFormatter(console_fmt)
        self.logger.addHandler(console)

        # File handler
        log_file = os.path.join(self.log_dir, "proxy_collector.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_fmt)
        self.logger.addHandler(file_handler)

        # Database handler
        self._db_handler = DatabaseLogHandler()
        self._db_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self._db_handler)

    def debug(self, msg: str, module: str = "") -> None:
        # Use a non-reserved extra key 'app_module' to avoid overwriting LogRecord
        # attributes (Python 3.14 disallows overwriting certain fields like 'module').
        self.logger.debug(msg, extra={"app_module": module or "general"})

    def info(self, msg: str, module: str = "") -> None:
        self.logger.info(msg, extra={"app_module": module or "general"})

    def success(self, msg: str, module: str = "") -> None:
        self.logger.log(25, msg, extra={"app_module": module or "general"})

    def warning(self, msg: str, module: str = "") -> None:
        self.logger.warning(msg, extra={"app_module": module or "general"})

    def error(self, msg: str, module: str = "") -> None:
        self.logger.error(msg, extra={"app_module": module or "general"})

    def set_level(self, level: str) -> None:
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "SUCCESS": 25,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }
        self.logger.setLevel(level_map.get(level, logging.INFO))

    def get_logs_file_path(self) -> str:
        return os.path.join(self.log_dir, "proxy_collector.log")

class DatabaseLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._db = None

    def emit(self, record):
        try:
            from core.database import Database
            if self._db is None:
                self._db = Database()

            # Prefer the app-provided module name (app_module) falling back to
            # the standard LogRecord.module if present.
            module_name = getattr(record, "app_module", getattr(record, "module", "general"))

            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                level=record.levelname,
                module=module_name,
                message=self.format(record)
            )
            self._db.insert_log(entry)

            event_bus.publish(AppEvent(
                event_type=EventType.LOG_ENTRY,
                data=entry,
                timestamp=datetime.now().isoformat()
            ))
        except Exception:
            pass

# Add custom SUCCESS level
logging.addLevelName(25, "SUCCESS")

def get_logger() -> AppLogger:
    return AppLogger()
