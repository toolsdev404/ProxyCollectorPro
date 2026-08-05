"""Proxy Collector Pro - Collect Page"""

import customtkinter as ctk
import threading
from typing import Dict, Any
from gui.components import ProgressWidget
from core.database import Database
from core.models import ValidationJob, Proxy
from core.events import event_bus, EventType, AppEvent
from engine.scheduler import FairScheduler
from engine.validator import ProxyValidator
from engine.collector import CollectionEngine
from sources.manager import SourceManager
from config.settings import Settings
from config.constants import Preset
from utils.logger import get_logger

logger = get_logger()


class CollectPage(ctk.CTkFrame):
    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db
        self.source_manager = SourceManager(db)
        self.scheduler = FairScheduler()
        self.validator = ProxyValidator()
        self.engine: CollectionEngine = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Control panel
        self.control_frame = ctk.CTkFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.control_frame.grid(
            row=0, column=0, padx=10, pady=10, sticky="ew"
        )

        # Preset selector
        ctk.CTkLabel(
            self.control_frame, text="Preset:", font=("Segoe UI", 12)
        ).pack(side="left", padx=10, pady=10)

        self.preset_combo = ctk.CTkComboBox(
            self.control_frame,
            values=["Fast", "Balanced", "Quality", "Deep"],
            command=self._on_preset_change,
            width=120
        )
        self.preset_combo.set("Balanced")
        self.preset_combo.pack(side="left", padx=5, pady=10)

        # Targets
        self.target_frame = ctk.CTkFrame(
            self.control_frame, fg_color="transparent"
        )
        self.target_frame.pack(side="left", padx=20, pady=10)

        self.targets: Dict[str, ctk.CTkEntry] = {}
        defaults = {"HTTP": "100", "HTTPS": "50", "SOCKS4": "25", "SOCKS5": "200"}
        for protocol in ["HTTP", "HTTPS", "SOCKS4", "SOCKS5"]:
            lbl = ctk.CTkLabel(
                self.target_frame, text=f"{protocol}:",
                font=("Segoe UI", 10)
            )
            lbl.pack(side="left", padx=(10, 2))
            entry = ctk.CTkEntry(self.target_frame, width=60, height=28)
            entry.insert(0, defaults[protocol])
            entry.pack(side="left", padx=(0, 10))
            self.targets[protocol.lower()] = entry

        # Buttons
        self.start_btn = ctk.CTkButton(
            self.control_frame, text="▶ Start",
            font=("Segoe UI", 12, "bold"),
            command=self._start_collection,
            fg_color="#27ae60", hover_color="#1e8449",
            width=100, height=35
        )
        self.start_btn.pack(side="right", padx=5, pady=10)

        self.pause_btn = ctk.CTkButton(
            self.control_frame, text="⏸ Pause",
            font=("Segoe UI", 12),
            command=self._pause_collection,
            state="disabled",
            width=100, height=35
        )
        self.pause_btn.pack(side="right", padx=5, pady=10)

        self.stop_btn = ctk.CTkButton(
            self.control_frame, text="⏹ Stop",
            font=("Segoe UI", 12),
            command=self._stop_collection,
            state="disabled",
            fg_color="#e74c3c", hover_color="#c0392b",
            width=100, height=35
        )
        self.stop_btn.pack(side="right", padx=5, pady=10)

        # Progress
        self.progress = ProgressWidget(self, "Collection Progress")
        self.progress.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # Stats display
        self.stats_frame = ctk.CTkFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.stats_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.stats_labels: Dict[str, ctk.CTkLabel] = {}
        stats = ["Found", "Validated", "Alive", "Dead",
                 "HTTP", "HTTPS", "SOCKS4", "SOCKS5"]
        for i, stat in enumerate(stats):
            lbl = ctk.CTkLabel(
                self.stats_frame, text=f"{stat}: 0",
                font=("Segoe UI", 12)
            )
            lbl.grid(row=0, column=i, padx=15, pady=10)
            self.stats_labels[stat.lower()] = lbl

        event_bus.subscribe(EventType.STATS_UPDATE, self._on_stats_update)
        event_bus.subscribe(EventType.COLLECTION_STARTED, self._on_collection_started)
        event_bus.subscribe(EventType.COLLECTION_STOPPED, self._on_collection_stopped)

    def _on_preset_change(self, preset_name: str) -> None:
        preset_map = {
            "Fast": Preset.FAST,
            "Balanced": Preset.BALANCED,
            "Quality": Preset.QUALITY,
            "Deep": Preset.DEEP
        }
        preset = preset_map.get(preset_name, Preset.BALANCED)
        settings = Settings.load()
        settings.apply_preset(preset)
        settings.save()
        logger.info(f"Applied preset: {preset_name}", "gui")

    def _start_collection(self) -> None:
        if self.engine and self.engine.is_running():
            return

        # Read targets
        targets = {}
        for protocol, entry in self.targets.items():
            try:
                targets[protocol] = int(entry.get())
            except ValueError:
                targets[protocol] = 100

        self.scheduler.set_targets(
            targets.get("http", 100),
            targets.get("https", 50),
            targets.get("socks4", 25),
            targets.get("socks5", 200),
            sum(targets.values())
        )
        self.scheduler.reset()

        # Fetch from sources
        self.progress.set_status("Fetching from sources...")

        def fetch_and_start():
            proxies = self.source_manager.fetch_all()
            if not proxies:
                self.after(0, lambda: self.progress.set_status(
                    "No proxies found from sources"
                ))
                return

            # Create validation jobs
            jobs = []
            for proxy in proxies:
                proxy_id = self.db.insert_proxy_sync(proxy)
                if proxy_id:
                    proxy.id = proxy_id
                job = ValidationJob(
                    proxy=proxy, protocol=proxy.protocol,
                    endpoint="", retries=0
                )
                jobs.append(job)

            self.scheduler.add_jobs(jobs)

            # Start engine
            self.engine = CollectionEngine(
                self.db, self.scheduler, self.validator
            )
            self.engine.start()

            self.after(0, lambda: self._update_ui_started())

        threading.Thread(target=fetch_and_start, daemon=True).start()

    def _update_ui_started(self) -> None:
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.progress.set_status("Collecting and validating...")

    def _pause_collection(self) -> None:
        if self.engine and self.engine.is_running():
            if self.engine.is_paused():
                self.engine.resume()
                self.pause_btn.configure(text="⏸ Pause")
            else:
                self.engine.pause()
                self.pause_btn.configure(text="▶ Resume")

    def _stop_collection(self) -> None:
        if self.engine:
            self.engine.stop()
            self.engine.join(timeout=5)
            self.engine = None

        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="⏸ Pause")
        self.stop_btn.configure(state="disabled")
        self.progress.set_progress(0, "Stopped")

    def _on_stats_update(self, event: AppEvent) -> None:
        stats = event.data
        self.after(0, lambda: self._update_stats_display(stats))

    def _update_stats_display(self, stats: Dict[str, Any]) -> None:
        self.stats_labels["found"].configure(
            text=f"Found: {stats.get('found', 0)}"
        )
        self.stats_labels["validated"].configure(
            text=f"Validated: {stats.get('validated', 0)}"
        )
        self.stats_labels["alive"].configure(
            text=f"Alive: {stats.get('alive', 0)}"
        )
        self.stats_labels["dead"].configure(
            text=f"Dead: {stats.get('dead', 0)}"
        )

        by_proto = stats.get("by_protocol", {})
        for p in ["http", "https", "socks4", "socks5"]:
            self.stats_labels[p].configure(
                text=f"{p.upper()}: {by_proto.get(p, 0)}"
            )

        total = stats.get("validated", 1)
        if total > 0:
            progress = stats.get("alive", 0) / total
            self.progress.set_progress(
                progress, f"Validated: {total}"
            )

    def _on_collection_started(self, event: AppEvent) -> None:
        self.after(0, lambda: self.progress.set_status("Collection started..."))

    def _on_collection_stopped(self, event: AppEvent) -> None:
        self.after(0, lambda: self._stop_collection())
