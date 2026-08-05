"""Proxy Collector Pro - Built-in Curated Sources"""

from typing import List, Dict, Any

BUILT_IN_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "ProxyList+ HTTP",
        "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "protocol": "http",
        "enabled": True,
        "priority": 8,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ProxyList+ HTTPS",
        "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/https.txt",
        "protocol": "https",
        "enabled": True,
        "priority": 8,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ProxyList+ SOCKS4",
        "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "protocol": "socks4",
        "enabled": True,
        "priority": 7,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ProxyList+ SOCKS5",
        "url": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "protocol": "socks5",
        "enabled": True,
        "priority": 7,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "Monosans HTTP",
        "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "protocol": "http",
        "enabled": True,
        "priority": 8,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "Monosans SOCKS4",
        "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "protocol": "socks4",
        "enabled": True,
        "priority": 7,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "Monosans SOCKS5",
        "url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "protocol": "socks5",
        "enabled": True,
        "priority": 7,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ProxyScrape HTTP",
        "url": "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "protocol": "http",
        "enabled": True,
        "priority": 9,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ProxyScrape SOCKS4",
        "url": "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all",
        "protocol": "socks4",
        "enabled": True,
        "priority": 8,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ProxyScrape SOCKS5",
        "url": "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all",
        "protocol": "socks5",
        "enabled": True,
        "priority": 8,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "Clarketm HTTP",
        "url": "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "protocol": "http",
        "enabled": True,
        "priority": 6,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ShiftyTR HTTP",
        "url": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "protocol": "http",
        "enabled": True,
        "priority": 6,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ShiftyTR SOCKS4",
        "url": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "protocol": "socks4",
        "enabled": True,
        "priority": 5,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "ShiftyTR SOCKS5",
        "url": "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "protocol": "socks5",
        "enabled": True,
        "priority": 5,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "OpenProxyList HTTP",
        "url": "https://raw.githubusercontent.com/openproxylist/main/main/proxies/http.txt",
        "protocol": "http",
        "enabled": True,
        "priority": 6,
        "is_custom": False,
        "parse_pattern": "plain"
    },
    {
        "name": "OpenProxyList SOCKS5",
        "url": "https://raw.githubusercontent.com/openproxylist/main/main/proxies/socks5.txt",
        "protocol": "socks5",
        "enabled": True,
        "priority": 5,
        "is_custom": False,
        "parse_pattern": "plain"
    },
]
