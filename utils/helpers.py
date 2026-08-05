"""Proxy Collector Pro - Helper Utilities"""

import re
import ipaddress
import socket
import hashlib
import random
import string
from typing import List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse

IP_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

PROXY_PATTERN = re.compile(
    r"(?:(?P<protocol>http(?:s)?|socks[45])://)?"
    r"(?:(?P<user>[^:@]+):(?P<pass>[^:@]+)@)?"
    r"(?P<host>(?:\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9.-]+)"
    r":(?P<port>\d{1,5})"
)

PROXY_TABLE_PATTERN = re.compile(
    r"(?P<host>(?:\d{1,3}\.){3}\d{1,3})[\s\t:]+(?P<port>\d{2,5})"
)

def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def is_valid_port(port: int) -> bool:
    return 1 <= port <= 65535

def parse_proxy_string(text: str, default_protocol: str = "http") -> Optional[Dict[str, Any]]:
    """Parse a proxy string into components."""
    text = text.strip()
    if not text:
        return None

    match = PROXY_PATTERN.match(text)
    if not match:
        # Try table format
        match = PROXY_TABLE_PATTERN.search(text)
        if not match:
            return None
        host = match.group("host")
        port = int(match.group("port"))
        protocol = default_protocol
    else:
        host = match.group("host")
        port = int(match.group("port"))
        protocol = match.group("protocol") or default_protocol

    if not is_valid_ip(host) and not is_valid_hostname(host):
        return None
    if not is_valid_port(port):
        return None

    return {
        "host": host,
        "port": port,
        "protocol": protocol.lower(),
    }

def is_valid_hostname(hostname: str) -> bool:
    if len(hostname) > 253:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def parse_proxy_list(text: str, source: str = "", source_url: str = "") -> List[Dict[str, Any]]:
    """Parse a block of text containing multiple proxies."""
    proxies = []
    seen = set()

    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parsed = parse_proxy_string(line)
        if parsed:
            key = f"{parsed['host']}:{parsed['port']}:{parsed['protocol']}"
            if key not in seen:
                seen.add(key)
                parsed["source"] = source
                parsed["source_url"] = source_url
                proxies.append(parsed)

    return proxies

def parse_html_for_proxies(html: str, source: str = "", source_url: str = "") -> List[Dict[str, Any]]:
    """Extract proxies from HTML content."""
    proxies = []
    seen = set()

    # Pattern 1: IP:PORT in various formats
    pattern = re.compile(
        r"(?P<host>(?:\d{1,3}\.){3}\d{1,3})"
        r"[\s\t:<>/\-]+"
        r"(?P<port>\d{2,5})"
    )

    for match in pattern.finditer(html):
        host = match.group("host")
        port = int(match.group("port"))

        if is_valid_ip(host) and is_valid_port(port):
            key = f"{host}:{port}"
            if key not in seen:
                seen.add(key)
                proxies.append({
                    "host": host,
                    "port": port,
                    "protocol": "http",
                    "source": source,
                    "source_url": source_url,
                })

    return proxies

def format_proxy_url(host: str, port: int, protocol: str, with_scheme: bool = True) -> str:
    if with_scheme:
        return f"{protocol}://{host}:{port}"
    return f"{host}:{port}"

def generate_id(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

def calculate_score(latency: float, reliability: float, freshness_hours: float, 
                   protocol_count: int, validation_count: int) -> int:
    """Calculate quality score 0-100."""
    from config.constants import WEIGHT_LATENCY, WEIGHT_RELIABILITY, WEIGHT_FRESHNESS, WEIGHT_PROTOCOLS, WEIGHT_REPEATED

    # Latency score (lower is better, max 10s)
    lat_score = max(0, 100 - (latency * 10)) if latency > 0 else 0

    # Reliability score
    rel_score = reliability * 100

    # Freshness score (newer is better, decays over 24h)
    fresh_score = max(0, 100 - (freshness_hours * 4.17))

    # Protocol diversity
    proto_score = min(100, protocol_count * 25)

    # Validation history
    val_score = min(100, validation_count * 10)

    total = (
        lat_score * WEIGHT_LATENCY +
        rel_score * WEIGHT_RELIABILITY +
        fresh_score * WEIGHT_FRESHNESS +
        proto_score * WEIGHT_PROTOCOLS +
        val_score * WEIGHT_REPEATED
    )
    return min(100, max(0, int(total)))

def truncate_string(s: str, max_len: int = 50) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + "..."

def format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def deduplicate_proxies(proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for p in proxies:
        key = f"{p.get('host')}:{p.get('port')}:{p.get('protocol', 'http')}"
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique
