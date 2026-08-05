"""Proxy Collector Pro - Settings Management"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from config.constants import (
    SETTINGS_FILE, DEFAULT_HTTP_ENDPOINTS, DEFAULT_HTTPS_ENDPOINTS,
    Preset, ValidationMode, ExportFormat, ExportScheme, ExportGrouping
)

@dataclass
class Settings:
    # General
    theme: str = "dark"
    language: str = "en"
    auto_start: bool = False
    minimize_to_tray: bool = False

    # Collection
    preset: str = Preset.BALANCED.value
    validation_mode: str = ValidationMode.BALANCED.value
    threads: int = 100
    timeout: int = 10
    max_retries: int = 3
    retry_delay: int = 1

    # Targets
    target_http: int = 100
    target_https: int = 50
    target_socks4: int = 25
    target_socks5: int = 200
    target_total: int = 500

    # Endpoints
    http_endpoints: List[str] = field(default_factory=lambda: DEFAULT_HTTP_ENDPOINTS.copy())
    https_endpoints: List[str] = field(default_factory=lambda: DEFAULT_HTTPS_ENDPOINTS.copy())

    # GeoIP
    geoip_enabled: bool = False
    geoip_timeout: int = 5

    # Export
    default_export_format: str = ExportFormat.TXT.value
    default_export_scheme: str = ExportScheme.WITH_SCHEME.value
    default_export_grouping: str = ExportGrouping.SEPARATE.value
    export_directory: str = ""

    # Advanced
    db_batch_size: int = 100
    ui_batch_size: int = 50
    connection_pool_size: int = 50
    session_reuse: bool = True
    dns_cache: bool = True

    # Logging
    log_level: str = "INFO"
    log_max_size_mb: int = 10
    log_backup_count: int = 5

    def __post_init__(self):
        if not self.export_directory:
            self.export_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        # Filter only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def save(self) -> None:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls) -> "Settings":
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception:
                pass
        settings = cls()
        settings.save()
        return settings

    def apply_preset(self, preset: Preset) -> None:
        presets = {
            Preset.FAST: {"threads": 200, "timeout": 5, "validation_mode": ValidationMode.FAST.value},
            Preset.BALANCED: {"threads": 100, "timeout": 10, "validation_mode": ValidationMode.SINGLE.value},
            Preset.QUALITY: {"threads": 50, "timeout": 15, "validation_mode": ValidationMode.DOUBLE.value},
            Preset.DEEP: {"threads": 25, "timeout": 20, "validation_mode": ValidationMode.STABILITY.value},
        }
        if preset in presets:
            for key, value in presets[preset].items():
                setattr(self, key, value)
            self.preset = preset.value
