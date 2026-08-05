"""Proxy Collector Pro - Collection Engine"""

import time
import queue
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from config.settings import Settings
from config.constants import Protocol, ValidationMode
from core.models import Proxy, ValidationJob, ValidationResult
from core.database import Database
from core.events import event_bus, EventType, AppEvent
from engine.validator import ProxyValidator
from engine.scheduler import FairScheduler
from engine.geoip import GeoIPResolver
from utils.logger import get_logger
from utils.helpers import parse_proxy_list, parse_html_for_proxies, deduplicate_proxies

logger = get_logger()

class CollectionEngine(threading.Thread):
    """Main collection and validation engine."""

    def __init__(self, db: Database, scheduler: FairScheduler, validator: ProxyValidator):
        super().__init__(daemon=True, name="CollectionEngine")
        self.db = db
        self.scheduler = scheduler
        self.validator = validator
        self.geoip = GeoIPResolver()
        self.settings = Settings.load()

        self._running = False
        self._paused = False
        self._stopped = False
        self._workers: List[threading.Thread] = []
        self._executor: Optional[ThreadPoolExecutor] = None
        self._result_queue: queue.Queue = queue.Queue()
        self._db_queue: queue.Queue = queue.Queue()
        self._stats = {
            "started": None,
            "found": 0,
            "validated": 0,
            "alive": 0,
            "dead": 0,
            "by_protocol": {p.value: 0 for p in Protocol},
        }
        self._stats_lock = threading.Lock()
        self._db_writer_thread: Optional[threading.Thread] = None

    def run(self) -> None:
        self._running = True
        self._stopped = False
        self._stats["started"] = datetime.now().isoformat()

        logger.info("Collection engine started", "collector")
        event_bus.publish(AppEvent(
            event_type=EventType.COLLECTION_STARTED,
            data=self._stats.copy(),
            timestamp=datetime.now().isoformat()
        ))

        # Start DB writer thread
        self._db_writer_thread = threading.Thread(target=self._db_writer_loop, daemon=True, name="DBWriterLoop")
        self._db_writer_thread.start()

        # Start result processor
        result_thread = threading.Thread(target=self._result_processor, daemon=True, name="ResultProcessor")
        result_thread.start()

        # Start worker threads
        self._executor = ThreadPoolExecutor(max_workers=self.settings.threads, thread_name_prefix="Validator")

        futures = set()

        while self._running and not self._stopped:
            if self._paused:
                time.sleep(0.1)
                continue

            # Check if all targets reached
            if self.scheduler.all_targets_reached():
                logger.success("All targets reached. Stopping collection.", "collector")
                break

            # Get next job
            job = self.scheduler.get_job()
            if job is None:
                if futures:
                    # Wait for some futures to complete
                    done, futures = self._wait_for_futures(futures, timeout=0.5, max_wait=5)
                    for future in done:
                        try:
                            result = future.result()
                            if result:
                                self._result_queue.put(result)
                        except Exception as e:
                            logger.debug(f"Future error: {e}", "collector")
                else:
                    time.sleep(0.1)
                continue

            # Submit validation job
            future = self._executor.submit(self._validate_job, job)
            futures.add(future)

            # Clean up completed futures periodically
            if len(futures) >= self.settings.threads * 2:
                done, futures = self._wait_for_futures(futures, timeout=0.1, max_wait=1)
                for future in done:
                    try:
                        result = future.result()
                        if result:
                            self._result_queue.put(result)
                    except Exception as e:
                        logger.debug(f"Future error: {e}", "collector")

        # Wait for remaining futures
        if futures:
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    if result:
                        self._result_queue.put(result)
                except Exception:
                    pass

        # Signal result processor to finish
        self._result_queue.put(None)
        result_thread.join(timeout=10)

        # Signal DB writer to finish
        self._db_queue.put(None)
        if self._db_writer_thread:
            self._db_writer_thread.join(timeout=10)

        if self._executor:
            self._executor.shutdown(wait=True)

        self._running = False
        logger.info("Collection engine stopped", "collector")
        event_bus.publish(AppEvent(
            event_type=EventType.COLLECTION_STOPPED,
            data=self._stats.copy(),
            timestamp=datetime.now().isoformat()
        ))

    def _validate_job(self, job: ValidationJob) -> Optional[ValidationResult]:
        try:
            result = self.validator.validate(job.proxy, job.protocol)

            with self._stats_lock:
                self._stats["validated"] += 1
                if result.success:
                    self._stats["alive"] += 1
                    self._stats["by_protocol"][result.protocol] = self._stats["by_protocol"].get(result.protocol, 0) + 1
                else:
                    self._stats["dead"] += 1

            return result
        except Exception as e:
            logger.debug(f"Validation error: {e}", "collector")
            return None

    def _result_processor(self) -> None:
        batch = []
        while True:
            try:
                result = self._result_queue.get(timeout=1)
                if result is None:
                    break
                batch.append(result)

                if len(batch) >= self.settings.db_batch_size:
                    self._process_batch(batch)
                    batch = []
            except queue.Empty:
                if batch:
                    self._process_batch(batch)
                    batch = []

        if batch:
            self._process_batch(batch)

    def _process_batch(self, results: List[ValidationResult]) -> None:
        proxies_to_update = []
        history_entries = []

        for result in results:
            proxy = result.proxy

            if result.success:
                proxy.status = "alive"
                proxy.latency = result.latency
                proxy.success_count += 1
                proxy.anonymity = result.anonymity

                # Update protocol capability
                self.db.set_protocol_capability(proxy.id, result.protocol, True, result.latency)

                # GeoIP (optional, failure ignored)
                if self.settings.geoip_enabled:
                    try:
                        geo = self.geoip.resolve(proxy.host)
                        if geo:
                            proxy.country = geo.get("country", "")
                            proxy.city = geo.get("city", "")
                            proxy.isp = geo.get("isp", "")
                            proxy.asn = geo.get("asn", "")
                            proxy.organization = geo.get("organization", "")
                    except Exception:
                        pass

                # Calculate score
                from utils.helpers import calculate_score
                proxy.score = calculate_score(
                    proxy.latency,
                    proxy.success_rate / 100,
                    0,  # freshness handled by DB
                    len(self.db.get_protocol_capabilities(proxy.id)),
                    proxy.success_count + proxy.fail_count
                )

                self.scheduler.mark_success(result.protocol)

            else:
                proxy.fail_count += 1
                if proxy.fail_count >= 3 and proxy.success_count == 0:
                    proxy.status = "dead"

                self.db.set_protocol_capability(proxy.id, result.protocol, False, 0)

            proxies_to_update.append(proxy)

            history_entries.append({
                "proxy_id": proxy.id,
                "timestamp": result.timestamp,
                "event": "validated",
                "protocol": result.protocol,
                "success": result.success,
                "latency": result.latency,
                "endpoint": result.endpoint_used,
                "error": result.error,
            })

        # Queue DB updates
        self._db_queue.put(("update_proxies", proxies_to_update))
        self._db_queue.put(("insert_history", history_entries))

        # Publish events
        event_bus.publish(AppEvent(
            event_type=EventType.STATS_UPDATE,
            data=self.get_stats(),
            timestamp=datetime.now().isoformat()
        ))

    def _db_writer_loop(self) -> None:
        while True:
            try:
                item = self._db_queue.get(timeout=1)
                if item is None:
                    break

                operation, data = item
                if operation == "update_proxies":
                    self.db.update_proxies_batch(data)
                elif operation == "insert_history":
                    for entry_data in data:
                        from core.models import HistoryEntry
                        entry = HistoryEntry(**entry_data)
                        self.db.insert_history(entry)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"DB writer error: {e}", "collector")

    def _wait_for_futures(self, futures, timeout=0.1, max_wait=5):
        import concurrent.futures
        start = time.time()
        done = set()
        remaining = futures.copy()

        while remaining and (time.time() - start) < max_wait:
            just_done, remaining = concurrent.futures.wait(
                remaining, timeout=timeout, return_when=concurrent.futures.FIRST_COMPLETED
            )
            done.update(just_done)
            if len(done) >= len(futures) // 2:
                break

        return done, remaining

    def pause(self) -> None:
        self._paused = True
        self.scheduler.pause()
        event_bus.publish(AppEvent(
            event_type=EventType.COLLECTION_PAUSED,
            data=None,
            timestamp=datetime.now().isoformat()
        ))

    def resume(self) -> None:
        self._paused = False
        self.scheduler.resume()
        event_bus.publish(AppEvent(
            event_type=EventType.COLLECTION_RESUMED,
            data=None,
            timestamp=datetime.now().isoformat()
        ))

    def stop(self) -> None:
        self._stopped = True
        self._running = False
        self.scheduler.stop()

    def get_stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            return self._stats.copy()

    def is_running(self) -> bool:
        return self._running and not self._stopped

    def is_paused(self) -> bool:
        return self._paused
