"""Proxy Collector Pro - Export Engine"""

import os
import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.settings import Settings
from config.constants import ExportFormat, ExportScheme, ExportGrouping, EXPORTS_DIR
from core.models import Proxy, ExportConfig
from core.database import Database
from core.events import event_bus, EventType, AppEvent
from utils.logger import get_logger

logger = get_logger()

class ExportEngine:
    def __init__(self, db: Database):
        self.db = db
        self.settings = Settings.load()

    def export(self, config: ExportConfig) -> Dict[str, Any]:
        """Export proxies based on configuration."""
        result = {
            "success": False,
            "files": [],
            "total": 0,
            "error": "",
        }

        try:
            # Build filters
            filters = config.filters or {}
            if config.protocols:
                # Will handle per-protocol
                pass

            proxies = self.db.get_all_proxies(filters)

            if not proxies:
                result["error"] = "No proxies match the selected filters"
                return result

            # Filter by protocols if specified
            if config.protocols:
                proxies = [p for p in proxies if p.protocol in config.protocols]

            if not proxies:
                result["error"] = "No proxies match the selected protocols"
                return result

            # Determine output path
            output_dir = config.output_path or self.settings.export_directory or EXPORTS_DIR
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if config.grouping == ExportGrouping.GROUPED.value:
                # Group by protocol, single file
                files = self._export_grouped(proxies, config, output_dir, timestamp)
                result["files"] = files
                result["total"] = len(proxies)
            elif config.grouping == ExportGrouping.SEPARATE.value:
                # Separate file per protocol
                files = self._export_separate(proxies, config, output_dir, timestamp)
                result["files"] = files
                result["total"] = len(proxies)
            else:  # BOTH
                files_grouped = self._export_grouped(proxies, config, output_dir, timestamp)
                files_separate = self._export_separate(proxies, config, output_dir, timestamp)
                result["files"] = files_grouped + files_separate
                result["total"] = len(proxies)

            result["success"] = True

            event_bus.publish(AppEvent(
                event_type=EventType.EXPORT_COMPLETED,
                data=result,
                timestamp=datetime.now().isoformat()
            ))

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Export failed: {e}", "export")

        return result

    def _export_grouped(self, proxies: List[Proxy], config: ExportConfig, 
                        output_dir: str, timestamp: str) -> List[str]:
        """Export all proxies into a single combined file, grouped by protocol within."""
        files = []

        # Group by protocol for organized output
        by_protocol: Dict[str, List[Proxy]] = {}
        for p in proxies:
            by_protocol.setdefault(p.protocol, []).append(p)

        filename = f"proxies_grouped_{timestamp}.{config.format}"
        filepath = os.path.join(output_dir, filename)

        if config.format == ExportFormat.TXT.value:
            with open(filepath, "w", encoding="utf-8") as f:
                for protocol in sorted(by_protocol.keys()):
                    f.write(f"# {protocol.upper()}\n")
                    for p in by_protocol[protocol]:
                        if config.scheme == ExportScheme.WITH_SCHEME.value:
                            f.write(f"{p.url}\n")
                        elif config.scheme == ExportScheme.WITHOUT_SCHEME.value:
                            f.write(f"{p.url_no_scheme}\n")
                        else:  # BOTH
                            f.write(f"{p.url}\n")
                            f.write(f"{p.url_no_scheme}\n")
                    f.write("\n")
        elif config.format == ExportFormat.CSV.value:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "host", "port", "protocol", "status", "anonymity", "country",
                    "city", "isp", "latency", "score", "source"
                ])
                for protocol in sorted(by_protocol.keys()):
                    for p in by_protocol[protocol]:
                        writer.writerow([
                            p.host, p.port, p.protocol, p.status, p.anonymity, p.country,
                            p.city, p.isp, p.latency, p.score, p.source
                        ])
        elif config.format == ExportFormat.JSON.value:
            data = []
            for protocol in sorted(by_protocol.keys()):
                data.extend([p.to_dict() for p in by_protocol[protocol]])
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        files.append(filepath)
        return files

    def _export_separate(self, proxies: List[Proxy], config: ExportConfig,
                         output_dir: str, timestamp: str) -> List[str]:
        files = []

        # Group by protocol
        by_protocol: Dict[str, List[Proxy]] = {}
        for p in proxies:
            by_protocol.setdefault(p.protocol, []).append(p)

        for protocol, protocol_proxies in by_protocol.items():
            filename = f"proxies_{protocol}_{timestamp}.{config.format}"
            filepath = os.path.join(output_dir, filename)

            if config.format == ExportFormat.TXT.value:
                self._write_txt(filepath, protocol_proxies, config.scheme)
            elif config.format == ExportFormat.CSV.value:
                self._write_csv(filepath, protocol_proxies)
            elif config.format == ExportFormat.JSON.value:
                self._write_json(filepath, protocol_proxies)

            files.append(filepath)

        return files

    def _write_txt(self, filepath: str, proxies: List[Proxy], scheme: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            for p in proxies:
                if scheme == ExportScheme.WITH_SCHEME.value:
                    f.write(f"{p.url}\n")
                elif scheme == ExportScheme.WITHOUT_SCHEME.value:
                    f.write(f"{p.url_no_scheme}\n")
                else:  # BOTH
                    f.write(f"{p.url}\n")
                    f.write(f"{p.url_no_scheme}\n")

    def _write_csv(self, filepath: str, proxies: List[Proxy]) -> None:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "host", "port", "protocol", "status", "anonymity", "country",
                "city", "isp", "latency", "score", "source"
            ])
            for p in proxies:
                writer.writerow([
                    p.host, p.port, p.protocol, p.status, p.anonymity, p.country,
                    p.city, p.isp, p.latency, p.score, p.source
                ])

    def _write_json(self, filepath: str, proxies: List[Proxy]) -> None:
        data = [p.to_dict() for p in proxies]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def quick_export(self, proxies: List[Proxy], format_type: str = "txt") -> str:
        """Quick export to default location."""
        config = ExportConfig(
            format=format_type,
            scheme=ExportScheme.WITH_SCHEME.value,
            grouping=ExportGrouping.SEPARATE.value,
            output_path=self.settings.export_directory or EXPORTS_DIR
        )
        result = self.export(config)
        if result["success"] and result["files"]:
            return result["files"][0]
        return ""
