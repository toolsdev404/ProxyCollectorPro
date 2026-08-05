"""Proxy Collector Pro - SQLite Database Engine (WAL Mode)"""

import sqlite3
import threading
import queue
import time
import json
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime
from contextlib import contextmanager
from core.models import Proxy, Source, HistoryEntry, LogEntry
from config.constants import DB_FILE, DB_BATCH_SIZE

class DatabaseWriter(threading.Thread):
    """Dedicated database writer thread for batch operations."""

    def __init__(self, db_path: str, batch_size: int = DB_BATCH_SIZE):
        super().__init__(daemon=True, name="DBWriter")
        self.db_path = db_path
        self.batch_size = batch_size
        self._queue: queue.Queue = queue.Queue()
        self._running = True
        self._lock = threading.Lock()
        self._pending_count = 0
        self._flush_event = threading.Event()
        self._last_flush = time.time()
        self._batch_interval = 0.5  # seconds
        self._connection: Optional[sqlite3.Connection] = None
        self._init_connection()

    def _init_connection(self) -> None:
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._connection.execute("PRAGMA cache_size=-64000")
        self._connection.execute("PRAGMA temp_store=MEMORY")
        self._connection.execute("PRAGMA mmap_size=268435456")
        self._connection.execute("PRAGMA page_size=4096")
        self._connection.commit()

    def enqueue(self, operation: Callable, args: Tuple = ()) -> None:
        self._queue.put((operation, args))
        with self._lock:
            self._pending_count += 1
        if self._pending_count >= self.batch_size:
            self._flush_event.set()

    def flush(self) -> None:
        self._flush_event.set()

    def stop(self) -> None:
        self._running = False
        self._flush_event.set()
        self.join(timeout=5.0)

    def run(self) -> None:
        batch = []
        while self._running:
            try:
                item = self._queue.get(timeout=0.1)
                batch.append(item)
            except queue.Empty:
                pass

            current_time = time.time()
            should_flush = (
                len(batch) >= self.batch_size or
                (batch and current_time - self._last_flush >= self._batch_interval) or
                self._flush_event.is_set()
            )

            if should_flush and batch:
                self._execute_batch(batch)
                batch = []
                with self._lock:
                    self._pending_count = 0
                self._flush_event.clear()
                self._last_flush = current_time

        # Final flush
        if batch:
            self._execute_batch(batch)

    def _execute_batch(self, batch: List[Tuple]) -> None:
        try:
            with self._connection:
                for operation, args in batch:
                    operation(self._connection, *args)
        except Exception as e:
            # Log error but don't crash
            print(f"DB batch error: {e}")

class Database:
    """Thread-safe SQLite database with WAL mode and batch writes."""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._local = threading.local()
        self._writer = DatabaseWriter(db_path)
        self._writer.start()
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_schema(self) -> None:
        conn = self._get_connection()
        with conn:
            # Proxies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT NOT NULL,
                    status TEXT DEFAULT 'unchecked',
                    anonymity TEXT DEFAULT 'unclassified',
                    country TEXT DEFAULT '',
                    city TEXT DEFAULT '',
                    isp TEXT DEFAULT '',
                    asn TEXT DEFAULT '',
                    organization TEXT DEFAULT '',
                    latency REAL DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    reliability REAL DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    first_seen TEXT,
                    last_seen TEXT,
                    last_checked TEXT,
                    source TEXT DEFAULT '',
                    source_url TEXT DEFAULT '',
                    is_custom INTEGER DEFAULT 0,
                    fingerprint TEXT NOT NULL,
                    UNIQUE(host, port, protocol)
                )
            """)

            # Sources table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    protocol TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 5,
                    health_score REAL DEFAULT 100,
                    last_check TEXT,
                    total_proxies INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    is_custom INTEGER DEFAULT 0,
                    parse_pattern TEXT DEFAULT ''
                )
            """)

            # History table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    event TEXT NOT NULL,
                    protocol TEXT,
                    success INTEGER DEFAULT 0,
                    latency REAL DEFAULT 0,
                    endpoint TEXT DEFAULT '',
                    error TEXT DEFAULT '',
                    FOREIGN KEY(proxy_id) REFERENCES proxies(id)
                )
            """)

            # Logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    module TEXT DEFAULT '',
                    message TEXT NOT NULL
                )
            """)

            # Protocol capabilities table (for deduplication)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS protocol_capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_id INTEGER NOT NULL,
                    protocol TEXT NOT NULL,
                    validated INTEGER DEFAULT 0,
                    latency REAL DEFAULT 0,
                    last_validated TEXT,
                    UNIQUE(proxy_id, protocol),
                    FOREIGN KEY(proxy_id) REFERENCES proxies(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_status ON proxies(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_protocol ON proxies(protocol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_country ON proxies(country)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_anonymity ON proxies(anonymity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_score ON proxies(score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_latency ON proxies(latency)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_source ON proxies(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_fingerprint ON proxies(fingerprint)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proxies_last_checked ON proxies(last_checked)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_proxy_id ON history(proxy_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_caps_proxy ON protocol_capabilities(proxy_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_caps_protocol ON protocol_capabilities(protocol)")

    def close(self) -> None:
        self._writer.stop()
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    # --- Proxy Operations ---

    def insert_proxy(self, proxy: Proxy) -> Optional[int]:
        """Async insert - returns None immediately, use insert_proxy_sync when ID is needed."""
        def _insert(conn, p):
            try:
                cursor = conn.execute("""
                    INSERT INTO proxies 
                    (host, port, protocol, status, anonymity, country, city, isp, asn, organization,
                     latency, score, reliability, success_count, fail_count, first_seen, last_seen,
                     last_checked, source, source_url, is_custom, fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(host, port, protocol) DO UPDATE SET
                        last_seen = excluded.last_seen,
                        status = CASE WHEN proxies.status = 'dead' THEN 'unchecked' ELSE proxies.status END,
                        source = COALESCE(NULLIF(excluded.source, ''), proxies.source),
                        source_url = COALESCE(NULLIF(excluded.source_url, ''), proxies.source_url)
                """, p.to_db_tuple())
                return cursor.lastrowid
            except Exception as e:
                return None

        proxy.first_seen = proxy.first_seen or datetime.now().isoformat()
        proxy.last_seen = datetime.now().isoformat()
        proxy.fingerprint  # ensure computed

        if threading.current_thread() is self._writer:
            return _insert(self._get_connection(), proxy)

        self._writer.enqueue(_insert, (proxy,))
        return None

    def insert_proxy_sync(self, proxy: Proxy) -> Optional[int]:
        """Synchronous insert that returns the proxy ID. Use when ID is needed immediately."""
        proxy.first_seen = proxy.first_seen or datetime.now().isoformat()
        proxy.last_seen = datetime.now().isoformat()
        proxy.fingerprint

        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                INSERT INTO proxies 
                (host, port, protocol, status, anonymity, country, city, isp, asn, organization,
                 latency, score, reliability, success_count, fail_count, first_seen, last_seen,
                 last_checked, source, source_url, is_custom, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(host, port, protocol) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    status = CASE WHEN proxies.status = 'dead' THEN 'unchecked' ELSE proxies.status END,
                    source = COALESCE(NULLIF(excluded.source, ''), proxies.source),
                    source_url = COALESCE(NULLIF(excluded.source_url, ''), proxies.source_url)
            """, proxy.to_db_tuple())
            conn.commit()

            # If it was an update, fetch the existing ID
            if cursor.lastrowid:
                proxy.id = cursor.lastrowid
                return cursor.lastrowid
            else:
                existing = self.get_proxy_by_endpoint(proxy.host, proxy.port, proxy.protocol)
                if existing:
                    proxy.id = existing.id
                    return existing.id
            return None
        except Exception as e:
            return None

    def insert_proxies_batch(self, proxies: List[Proxy]) -> None:
        def _insert_batch(conn, proxy_list):
            now = datetime.now().isoformat()
            data = []
            for p in proxy_list:
                p.first_seen = p.first_seen or now
                p.last_seen = now
                data.append(p.to_db_tuple())

            conn.executemany("""
                INSERT INTO proxies 
                (host, port, protocol, status, anonymity, country, city, isp, asn, organization,
                 latency, score, reliability, success_count, fail_count, first_seen, last_seen,
                 last_checked, source, source_url, is_custom, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(host, port, protocol) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    status = CASE WHEN proxies.status = 'dead' THEN 'unchecked' ELSE proxies.status END,
                    source = COALESCE(NULLIF(excluded.source, ''), proxies.source),
                    source_url = COALESCE(NULLIF(excluded.source_url, ''), proxies.source_url)
            """, data)

        self._writer.enqueue(_insert_batch, (proxies,))

    def update_proxy(self, proxy: Proxy) -> None:
        def _update(conn, p):
            conn.execute("""
                UPDATE proxies SET
                    status = ?, anonymity = ?, country = ?, city = ?, isp = ?,
                    asn = ?, organization = ?, latency = ?, score = ?,
                    reliability = ?, success_count = ?, fail_count = ?,
                    last_seen = ?, last_checked = ?
                WHERE id = ?
            """, (
                p.status, p.anonymity, p.country, p.city, p.isp,
                p.asn, p.organization, p.latency, p.score,
                p.reliability, p.success_count, p.fail_count,
                p.last_seen, p.last_checked, p.id
            ))

        proxy.last_seen = datetime.now().isoformat()
        proxy.last_checked = datetime.now().isoformat()
        self._writer.enqueue(_update, (proxy,))

    def update_proxies_batch(self, proxies: List[Proxy]) -> None:
        def _update_batch(conn, proxy_list):
            now = datetime.now().isoformat()
            for p in proxy_list:
                p.last_seen = now
                p.last_checked = now
                conn.execute("""
                    UPDATE proxies SET
                        status = ?, anonymity = ?, country = ?, city = ?, isp = ?,
                        asn = ?, organization = ?, latency = ?, score = ?,
                        reliability = ?, success_count = ?, fail_count = ?,
                        last_seen = ?, last_checked = ?
                    WHERE id = ?
                """, (
                    p.status, p.anonymity, p.country, p.city, p.isp,
                    p.asn, p.organization, p.latency, p.score,
                    p.reliability, p.success_count, p.fail_count,
                    p.last_seen, p.last_checked, p.id
                ))

        self._writer.enqueue(_update_batch, (proxies,))

    def get_proxy_by_id(self, proxy_id: int) -> Optional[Proxy]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM proxies WHERE id = ?", (proxy_id,)).fetchone()
        if row:
            return self._row_to_proxy(row)
        return None

    def get_proxy_by_endpoint(self, host: str, port: int, protocol: str) -> Optional[Proxy]:
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM proxies WHERE host = ? AND port = ? AND protocol = ?",
            (host, port, protocol)
        ).fetchone()
        if row:
            return self._row_to_proxy(row)
        return None

    def get_all_proxies(self, filters: Optional[Dict[str, Any]] = None) -> List[Proxy]:
        conn = self._get_connection()
        query = "SELECT * FROM proxies WHERE 1=1"
        params = []

        if filters:
            if "protocol" in filters and filters["protocol"]:
                query += " AND protocol = ?"
                params.append(filters["protocol"])
            if "status" in filters and filters["status"]:
                query += " AND status = ?"
                params.append(filters["status"])
            if "country" in filters and filters["country"]:
                query += " AND country = ?"
                params.append(filters["country"])
            if "anonymity" in filters and filters["anonymity"]:
                query += " AND anonymity = ?"
                params.append(filters["anonymity"])
            if "source" in filters and filters["source"]:
                query += " AND source = ?"
                params.append(filters["source"])
            if "min_score" in filters:
                query += " AND score >= ?"
                params.append(filters["min_score"])
            if "max_latency" in filters:
                query += " AND latency <= ?"
                params.append(filters["max_latency"])
            if "search" in filters and filters["search"]:
                query += " AND (host LIKE ? OR country LIKE ? OR city LIKE ? OR isp LIKE ?)"
                like = f"%{filters['search']}%"
                params.extend([like, like, like, like])

        query += " ORDER BY score DESC, latency ASC"

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_proxy(row) for row in rows]

    def get_proxies_count(self, status: Optional[str] = None) -> int:
        conn = self._get_connection()
        query = "SELECT COUNT(*) FROM proxies"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        return conn.execute(query, params).fetchone()[0]

    def get_protocol_counts(self) -> Dict[str, int]:
        conn = self._get_connection()
        rows = conn.execute("""
            SELECT protocol, COUNT(*) as count FROM proxies WHERE status = 'alive' GROUP BY protocol
        """).fetchall()
        return {row["protocol"]: row["count"] for row in rows}

    def delete_proxy(self, proxy_id: int) -> None:
        def _delete(conn, pid):
            conn.execute("DELETE FROM proxies WHERE id = ?", (pid,))
            conn.execute("DELETE FROM protocol_capabilities WHERE proxy_id = ?", (pid,))
        self._writer.enqueue(_delete, (proxy_id,))

    def delete_dead_proxies(self) -> int:
        def _delete_dead(conn):
            cursor = conn.execute("DELETE FROM proxies WHERE status = 'dead'")
            conn.commit()
            return cursor.rowcount

        conn = self._get_connection()
        return _delete_dead(conn)

    def clear_proxies(self) -> None:
        def _clear(conn):
            conn.execute("DELETE FROM proxies")
            conn.execute("DELETE FROM protocol_capabilities")
            conn.execute("DELETE FROM history")
            conn.commit()
        self._writer.enqueue(_clear)

    def _row_to_proxy(self, row: sqlite3.Row) -> Proxy:
        return Proxy(
            id=row["id"],
            host=row["host"],
            port=row["port"],
            protocol=row["protocol"],
            status=row["status"],
            anonymity=row["anonymity"],
            country=row["country"],
            city=row["city"],
            isp=row["isp"],
            asn=row["asn"],
            organization=row["organization"],
            latency=row["latency"],
            score=row["score"],
            reliability=row["reliability"],
            success_count=row["success_count"],
            fail_count=row["fail_count"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            last_checked=row["last_checked"],
            source=row["source"],
            source_url=row["source_url"],
            is_custom=bool(row["is_custom"]),
        )

    # --- Source Operations ---

    def insert_source(self, source: Source) -> Optional[int]:
        def _insert(conn, s):
            try:
                cursor = conn.execute("""
                    INSERT INTO sources (name, url, protocol, enabled, priority, health_score,
                        last_check, total_proxies, success_count, fail_count, is_custom, parse_pattern)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        url = excluded.url,
                        protocol = excluded.protocol,
                        enabled = excluded.enabled,
                        priority = excluded.priority,
                        is_custom = excluded.is_custom,
                        parse_pattern = excluded.parse_pattern
                """, (s.name, s.url, s.protocol, int(s.enabled), s.priority, s.health_score,
                      s.last_check, s.total_proxies, s.success_count, s.fail_count,
                      int(s.is_custom), s.parse_pattern))
                return cursor.lastrowid
            except Exception:
                return None

        self._writer.enqueue(_insert, (source,))
        return None

    def update_source(self, source: Source) -> None:
        def _update(conn, s):
            conn.execute("""
                UPDATE sources SET
                    name = ?, url = ?, protocol = ?, enabled = ?, priority = ?,
                    health_score = ?, last_check = ?, total_proxies = ?,
                    success_count = ?, fail_count = ?, is_custom = ?, parse_pattern = ?
                WHERE id = ?
            """, (s.name, s.url, s.protocol, int(s.enabled), s.priority, s.health_score,
                  s.last_check, s.total_proxies, s.success_count, s.fail_count,
                  int(s.is_custom), s.parse_pattern, s.id))
        self._writer.enqueue(_update, (source,))

    def get_all_sources(self) -> List[Source]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM sources ORDER BY priority DESC, name ASC").fetchall()
        return [self._row_to_source(row) for row in rows]

    def get_source_by_id(self, source_id: int) -> Optional[Source]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row:
            return self._row_to_source(row)
        return None

    def delete_source(self, source_id: int) -> None:
        def _delete(conn, sid):
            conn.execute("DELETE FROM sources WHERE id = ?", (sid,))
        self._writer.enqueue(_delete, (source_id,))

    def _row_to_source(self, row: sqlite3.Row) -> Source:
        return Source(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            protocol=row["protocol"],
            enabled=bool(row["enabled"]),
            priority=row["priority"],
            health_score=row["health_score"],
            last_check=row["last_check"],
            total_proxies=row["total_proxies"],
            success_count=row["success_count"],
            fail_count=row["fail_count"],
            is_custom=bool(row["is_custom"]),
            parse_pattern=row["parse_pattern"],
        )

    # --- History Operations ---

    def insert_history(self, entry: HistoryEntry) -> None:
        def _insert(conn, e):
            conn.execute("""
                INSERT INTO history (proxy_id, timestamp, event, protocol, success, latency, endpoint, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (e.proxy_id, e.timestamp, e.event, e.protocol, int(e.success), e.latency, e.endpoint, e.error))
        self._writer.enqueue(_insert, (entry,))

    def get_history_by_proxy(self, proxy_id: int, limit: int = 100) -> List[HistoryEntry]:
        conn = self._get_connection()
        rows = conn.execute("""
            SELECT * FROM history WHERE proxy_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (proxy_id, limit)).fetchall()
        return [HistoryEntry(
            id=row["id"], proxy_id=row["proxy_id"], timestamp=row["timestamp"],
            event=row["event"], protocol=row["protocol"], success=bool(row["success"]),
            latency=row["latency"], endpoint=row["endpoint"], error=row["error"]
        ) for row in rows]

    def get_history_stats(self, proxy_id: int) -> Dict[str, Any]:
        conn = self._get_connection()
        row = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                AVG(latency) as avg_latency,
                MIN(latency) as min_latency,
                MAX(latency) as max_latency
            FROM history WHERE proxy_id = ?
        """, (proxy_id,)).fetchone()
        return {
            "total": row["total"] or 0,
            "successes": row["successes"] or 0,
            "avg_latency": round(row["avg_latency"] or 0, 2),
            "min_latency": round(row["min_latency"] or 0, 2),
            "max_latency": round(row["max_latency"] or 0, 2),
        }

    # --- Log Operations ---

    def insert_log(self, entry: LogEntry) -> None:
        def _insert(conn, e):
            conn.execute("""
                INSERT INTO logs (timestamp, level, module, message)
                VALUES (?, ?, ?, ?)
            """, (e.timestamp, e.level, e.module, e.message))
        self._writer.enqueue(_insert, (entry,))

    def get_logs(self, level: Optional[str] = None, limit: int = 1000) -> List[LogEntry]:
        conn = self._get_connection()
        query = "SELECT * FROM logs"
        params = []
        if level:
            query += " WHERE level = ?"
            params.append(level)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [LogEntry(
            id=row["id"], timestamp=row["timestamp"], level=row["level"],
            module=row["module"], message=row["message"]
        ) for row in rows]

    def clear_logs(self) -> None:
        def _clear(conn):
            conn.execute("DELETE FROM logs")
        self._writer.enqueue(_clear)

    # --- Protocol Capabilities ---

    def set_protocol_capability(self, proxy_id: int, protocol: str, validated: bool, latency: float = 0) -> None:
        def _set(conn, pid, proto, val, lat):
            conn.execute("""
                INSERT INTO protocol_capabilities (proxy_id, protocol, validated, latency, last_validated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(proxy_id, protocol) DO UPDATE SET
                    validated = excluded.validated,
                    latency = excluded.latency,
                    last_validated = excluded.last_validated
            """, (pid, proto, int(val), lat, datetime.now().isoformat()))
        self._writer.enqueue(_set, (proxy_id, protocol, validated, latency))

    def get_protocol_capabilities(self, proxy_id: int) -> Dict[str, Dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM protocol_capabilities WHERE proxy_id = ?",
            (proxy_id,)
        ).fetchall()
        return {
            row["protocol"]: {
                "validated": bool(row["validated"]),
                "latency": row["latency"],
                "last_validated": row["last_validated"]
            }
            for row in rows
        }

    # --- Statistics ---

    def get_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        stats = {}

        # Total counts
        row = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'alive' THEN 1 ELSE 0 END) as alive,
                SUM(CASE WHEN status = 'dead' THEN 1 ELSE 0 END) as dead,
                SUM(CASE WHEN status = 'unchecked' THEN 1 ELSE 0 END) as unchecked
            FROM proxies
        """).fetchone()
        stats["total"] = row["total"] or 0
        stats["alive"] = row["alive"] or 0
        stats["dead"] = row["dead"] or 0
        stats["unchecked"] = row["unchecked"] or 0

        # Protocol breakdown
        stats["by_protocol"] = self.get_protocol_counts()

        # Source counts
        row = conn.execute("SELECT COUNT(*) FROM sources").fetchone()
        stats["sources"] = row[0] or 0

        # Average score and latency
        row = conn.execute("""
            SELECT AVG(score) as avg_score, AVG(latency) as avg_latency
            FROM proxies WHERE status = 'alive'
        """).fetchone()
        stats["avg_score"] = round(row["avg_score"] or 0, 1)
        stats["avg_latency"] = round(row["avg_latency"] or 0, 2)

        return stats

    # --- Maintenance ---

    def vacuum(self) -> None:
        def _vacuum(conn):
            conn.execute("VACUUM")
        self._writer.enqueue(_vacuum)

    def optimize(self) -> None:
        def _analyze(conn):
            conn.execute("ANALYZE")
        self._writer.enqueue(_analyze)

    def checkpoint(self) -> None:
        def _checkpoint(conn):
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._writer.enqueue(_checkpoint)
