"""Proxy Collector Pro - Data Models"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import hashlib
import json

class Protocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class ProxyStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"
    UNCHECKED = "unchecked"
    CHECKING = "checking"

class AnonymityLevel(Enum):
    ELITE = "elite"
    ANONYMOUS = "anonymous"
    TRANSPARENT = "transparent"
    UNCLASSIFIED = "unclassified"

@dataclass
class Proxy:
    id: Optional[int] = None
    host: str = ""
    port: int = 0
    protocol: str = ""
    status: str = ProxyStatus.UNCHECKED.value
    anonymity: str = AnonymityLevel.UNCLASSIFIED.value
    country: str = ""
    city: str = ""
    isp: str = ""
    asn: str = ""
    organization: str = ""
    latency: float = 0.0
    score: int = 0
    reliability: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    last_checked: Optional[str] = None
    source: str = ""
    source_url: str = ""
    is_custom: bool = False

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.endpoint}"

    @property
    def url_no_scheme(self) -> str:
        return self.endpoint

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(f"{self.host}:{self.port}".encode()).hexdigest()[:32]

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proxy":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_db_tuple(self) -> tuple:
        return (
            self.host, self.port, self.protocol, self.status, self.anonymity,
            self.country, self.city, self.isp, self.asn, self.organization,
            self.latency, self.score, self.reliability, self.success_count,
            self.fail_count, self.first_seen, self.last_seen, self.last_checked,
            self.source, self.source_url, self.is_custom, self.fingerprint
        )

@dataclass
class Source:
    id: Optional[int] = None
    name: str = ""
    url: str = ""
    protocol: str = ""
    enabled: bool = True
    priority: int = 5
    health_score: float = 100.0
    last_check: Optional[str] = None
    total_proxies: int = 0
    success_count: int = 0
    fail_count: int = 0
    is_custom: bool = False
    parse_pattern: str = ""

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Source":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class ValidationJob:
    proxy: Proxy
    protocol: str
    endpoint: str = ""
    retries: int = 0
    priority: int = 5

@dataclass
class ValidationResult:
    proxy: Proxy
    protocol: str
    success: bool
    latency: float = 0.0
    anonymity: str = AnonymityLevel.UNCLASSIFIED.value
    error: str = ""
    endpoint_used: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class HistoryEntry:
    id: Optional[int] = None
    proxy_id: int = 0
    timestamp: str = ""
    event: str = ""
    protocol: str = ""
    success: bool = False
    latency: float = 0.0
    endpoint: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class LogEntry:
    id: Optional[int] = None
    timestamp: str = ""
    level: str = ""
    module: str = ""
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ExportConfig:
    format: str = "txt"
    scheme: str = "with_scheme"
    grouping: str = "separate"
    protocols: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    output_path: str = ""
