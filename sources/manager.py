"""Proxy Collector Pro - Source Manager"""

import json
import time
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from config.settings import Settings
from config.constants import SOURCES_FILE
from core.models import Source, Proxy
from core.database import Database
from core.events import event_bus, EventType, AppEvent
from sources.built_in import BUILT_IN_SOURCES
from utils.logger import get_logger
from utils.helpers import parse_proxy_list, parse_html_for_proxies

logger = get_logger()

class SourceManager:
    def __init__(self, db: Database):
        self.db = db
        self._sources: List[Source] = []
        self._load_sources()

    def _load_sources(self) -> None:
        """Load sources from database, initialize built-in if empty."""
        db_sources = self.db.get_all_sources()

        if not db_sources:
            # Initialize with built-in sources
            for src_data in BUILT_IN_SOURCES:
                source = Source.from_dict(src_data)
                self.db.insert_source(source)
            db_sources = self.db.get_all_sources()

        self._sources = db_sources

    def get_all_sources(self) -> List[Source]:
        return self._sources.copy()

    def get_enabled_sources(self) -> List[Source]:
        return [s for s in self._sources if s.enabled]

    def add_source(self, source: Source) -> bool:
        if any(s.name == source.name for s in self._sources):
            return False
        source.is_custom = True
        self.db.insert_source(source)
        self._sources.append(source)
        event_bus.publish(AppEvent(
            event_type=EventType.SOURCE_ADDED,
            data=source.to_dict(),
            timestamp=datetime.now().isoformat()
        ))
        return True

    def update_source(self, source: Source) -> None:
        for i, s in enumerate(self._sources):
            if s.id == source.id:
                self._sources[i] = source
                break
        self.db.update_source(source)
        event_bus.publish(AppEvent(
            event_type=EventType.SOURCE_UPDATED,
            data=source.to_dict(),
            timestamp=datetime.now().isoformat()
        ))

    def delete_source(self, source_id: int) -> None:
        self._sources = [s for s in self._sources if s.id != source_id]
        self.db.delete_source(source_id)
        event_bus.publish(AppEvent(
            event_type=EventType.SOURCE_REMOVED,
            data={"id": source_id},
            timestamp=datetime.now().isoformat()
        ))

    def toggle_source(self, source_id: int) -> None:
        source = self.db.get_source_by_id(source_id)
        if source:
            source.enabled = not source.enabled
            self.update_source(source)

    def test_source(self, source: Source) -> Dict[str, Any]:
        """Test a source and return statistics."""
        result = {
            "source": source.name,
            "reachable": False,
            "proxies_found": 0,
            "error": "",
            "response_time": 0,
        }

        start = time.time()
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(source.url, headers=headers, timeout=15)
            result["response_time"] = round(time.time() - start, 2)

            if resp.status_code == 200:
                result["reachable"] = True

                if source.parse_pattern == "plain" or source.url.endswith(".txt"):
                    proxies = parse_proxy_list(resp.text, source.name, source.url)
                else:
                    proxies = parse_html_for_proxies(resp.text, source.name, source.url)

                result["proxies_found"] = len(proxies)

                # Update source stats
                source.last_check = datetime.now().isoformat()
                source.total_proxies = len(proxies)
                source.health_score = 100.0
                self.update_source(source)
            else:
                result["error"] = f"HTTP {resp.status_code}"
                source.health_score = max(0, source.health_score - 10)
                self.update_source(source)

        except Exception as e:
            result["error"] = str(e)[:100]
            source.health_score = max(0, source.health_score - 20)
            self.update_source(source)

        event_bus.publish(AppEvent(
            event_type=EventType.SOURCE_TESTED,
            data=result,
            timestamp=datetime.now().isoformat()
        ))

        return result

    def fetch_all(self) -> List[Proxy]:
        """Fetch proxies from all enabled sources."""
        all_proxies = []
        enabled = self.get_enabled_sources()

        logger.info(f"Fetching from {len(enabled)} enabled sources", "sources")

        for source in enabled:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                resp = requests.get(source.url, headers=headers, timeout=20)

                if resp.status_code == 200:
                    if source.parse_pattern == "plain" or source.url.endswith(".txt"):
                        parsed = parse_proxy_list(resp.text, source.name, source.url)
                    else:
                        parsed = parse_html_for_proxies(resp.text, source.name, source.url)

                    for p in parsed:
                        proxy = Proxy(
                            host=p["host"],
                            port=p["port"],
                            protocol=p.get("protocol", source.protocol or "http"),
                            source=p.get("source", source.name),
                            source_url=p.get("source_url", source.url),
                            status="unchecked"
                        )
                        all_proxies.append(proxy)

                    source.total_proxies = len(parsed)
                    source.success_count += 1
                    source.last_check = datetime.now().isoformat()
                    logger.success(f"Source '{source.name}': {len(parsed)} proxies", "sources")
                else:
                    source.fail_count += 1
                    logger.warning(f"Source '{source.name}': HTTP {resp.status_code}", "sources")

            except Exception as e:
                source.fail_count += 1
                logger.error(f"Source '{source.name}': {str(e)[:80]}", "sources")

            self.update_source(source)

        # Deduplicate
        from utils.helpers import deduplicate_proxies
        unique = []
        seen = set()
        for proxy in all_proxies:
            key = f"{proxy.host}:{proxy.port}:{proxy.protocol}"
            if key not in seen:
                seen.add(key)
                unique.append(proxy)

        logger.info(f"Total unique proxies fetched: {len(unique)}", "sources")
        return unique

    def export_sources(self, path: str) -> None:
        data = [s.to_dict() for s in self._sources]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_sources(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for src_data in data:
            source = Source.from_dict(src_data)
            source.is_custom = True
            if self.add_source(source):
                count += 1
        return count

    def reset_to_builtin(self) -> None:
        """Reset all sources to built-in defaults."""
        for s in self._sources:
            self.db.delete_source(s.id)
        self._sources = []

        for src_data in BUILT_IN_SOURCES:
            source = Source.from_dict(src_data)
            self.db.insert_source(source)

        self._sources = self.db.get_all_sources()
