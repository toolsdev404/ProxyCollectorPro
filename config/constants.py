"""Proxy Collector Pro - Application Constants"""

import os
from enum import Enum, auto

APP_NAME = "Proxy Collector Pro"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Elite Software Engineering Team"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOURCES_FILE = os.path.join(DATA_DIR, "sources.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DB_FILE = os.path.join(DATA_DIR, "proxy_collector.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Protocols
class Protocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

PROTOCOLS = [Protocol.HTTP, Protocol.HTTPS, Protocol.SOCKS4, Protocol.SOCKS5]

# Validation Modes
class ValidationMode(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    SINGLE = "single"
    DOUBLE = "double"
    STABILITY = "stability"

# Anonymity Levels
class AnonymityLevel(Enum):
    ELITE = "elite"
    ANONYMOUS = "anonymous"
    TRANSPARENT = "transparent"
    UNCLASSIFIED = "unclassified"

# Proxy Status
class ProxyStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"
    UNCHECKED = "unchecked"
    CHECKING = "checking"

# Log Levels
class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"

# Export Formats
class ExportFormat(Enum):
    TXT = "txt"
    CSV = "csv"
    JSON = "json"

# Export Options
class ExportScheme(Enum):
    WITH_SCHEME = "with_scheme"
    WITHOUT_SCHEME = "without_scheme"
    BOTH = "both"

class ExportGrouping(Enum):
    GROUPED = "grouped"
    SEPARATE = "separate"
    BOTH = "both"

# Presets
class Preset(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    DEEP = "deep"

# Validation Endpoints
DEFAULT_HTTP_ENDPOINTS = [
    "http://httpbin.org/ip",
    "http://icanhazip.com",
    "http://checkip.amazonaws.com",
]

DEFAULT_HTTPS_ENDPOINTS = [
    "https://httpbin.org/ip",
    "https://icanhazip.com",
    "https://checkip.amazonaws.com",
    "https://api.ipify.org",
]

# Timeouts (seconds)
TIMEOUT_FAST = 5
TIMEOUT_BALANCED = 10
TIMEOUT_QUALITY = 15
TIMEOUT_DEEP = 20

# Thread Pool Sizes
THREADS_FAST = 200
THREADS_BALANCED = 100
THREADS_QUALITY = 50
THREADS_DEEP = 25

# Retry Settings
MAX_RETRIES = 3
RETRY_DELAY = 1

# Batch Sizes
DB_BATCH_SIZE = 100
UI_BATCH_SIZE = 50

# Quality Score Weights
WEIGHT_LATENCY = 0.35
WEIGHT_RELIABILITY = 0.30
WEIGHT_FRESHNESS = 0.15
WEIGHT_PROTOCOLS = 0.10
WEIGHT_REPEATED = 0.10

# GeoIP
GEOIP_TIMEOUT = 5
GEOIP_MAX_RETRIES = 2

# UI
WINDOW_MIN_WIDTH = 1280
WINDOW_MIN_HEIGHT = 800
SIDEBAR_WIDTH = 220
TABLE_ROW_HEIGHT = 28

# Colors (Dark Theme)
DARK_BG = "#1a1a2e"
DARK_CARD = "#16213e"
DARK_ACCENT = "#0f3460"
DARK_TEXT = "#e94560"
DARK_SUCCESS = "#00d9ff"
DARK_WARNING = "#f39c12"
DARK_ERROR = "#e74c3c"

# Colors (Light Theme)
LIGHT_BG = "#f5f6fa"
LIGHT_CARD = "#ffffff"
LIGHT_ACCENT = "#3498db"
LIGHT_TEXT = "#2c3e50"
LIGHT_SUCCESS = "#27ae60"
LIGHT_WARNING = "#f39c12"
LIGHT_ERROR = "#e74c3c"
