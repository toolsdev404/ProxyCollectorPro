"""Proxy Collector Pro - Dashboard Page"""

import customtkinter as ctk
from typing import Dict, Any
from gui.components import StatCard, ProgressWidget
from core.database import Database
from core.events import event_bus, EventType, AppEvent
from utils.logger import get_logger

logger = get_logger()


class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db

        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Stats cards
        self.card_total = StatCard(
            self, "Total Proxies", "0", "All time collected", "📊", "#3498db"
        )
        self.card_total.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.card_alive = StatCard(
            self, "Alive", "0", "Currently working", "✅", "#27ae60"
        )
        self.card_alive.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.card_dead = StatCard(
            self, "Dead", "0", "Failed validation", "❌", "#e74c3c"
        )
        self.card_dead.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        self.card_sources = StatCard(
            self, "Sources", "0", "Active sources", "🌐", "#9b59b6"
        )
        self.card_sources.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")

        # Bottom section
        self.bottom_frame = ctk.CTkFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.bottom_frame.grid(
            row=1, column=0, columnspan=4, padx=10, pady=10, sticky="nsew"
        )
        self.bottom_frame.grid_columnconfigure((0, 1), weight=1)
        self.bottom_frame.grid_rowconfigure(1, weight=1)

        # Protocol breakdown
        self.protocol_frame = ctk.CTkFrame(
            self.bottom_frame, fg_color="transparent"
        )
        self.protocol_frame.grid(
            row=0, column=0, padx=15, pady=15, sticky="nsew"
        )

        ctk.CTkLabel(
            self.protocol_frame,
            text="Protocol Distribution",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))

        self.protocol_bars: Dict[str, ctk.CTkProgressBar] = {}
        self.protocol_labels: Dict[str, ctk.CTkLabel] = {}

        for protocol in ["http", "https", "socks4", "socks5"]:
            frame = ctk.CTkFrame(self.protocol_frame, fg_color="transparent")
            frame.pack(fill="x", pady=3)

            lbl = ctk.CTkLabel(
                frame, text=protocol.upper(),
                font=("Segoe UI", 11), width=80
            )
            lbl.pack(side="left")

            bar = ctk.CTkProgressBar(
                frame, height=16, corner_radius=8, width=200
            )
            bar.pack(side="left", padx=10)
            bar.set(0)

            count_lbl = ctk.CTkLabel(
                frame, text="0",
                font=("Segoe UI", 11, "bold"), width=50
            )
            count_lbl.pack(side="left")

            self.protocol_bars[protocol] = bar
            self.protocol_labels[protocol] = count_lbl

        # Recent activity
        self.activity_frame = ctk.CTkFrame(
            self.bottom_frame, fg_color="transparent"
        )
        self.activity_frame.grid(
            row=0, column=1, padx=15, pady=15, sticky="nsew"
        )

        ctk.CTkLabel(
            self.activity_frame,
            text="Recent Activity",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))

        self.activity_text = ctk.CTkTextbox(
            self.activity_frame, height=200, font=("Consolas", 10)
        )
        self.activity_text.pack(fill="both", expand=True)
        self.activity_text.configure(state="disabled")

        # Subscribe to events
        event_bus.subscribe(EventType.STATS_UPDATE, self._on_stats_update)
        event_bus.subscribe(EventType.LOG_ENTRY, self._on_log_entry)

        self.refresh()

    def refresh(self) -> None:
        stats = self.db.get_stats()
        self.card_total.set_value(str(stats.get("total", 0)))
        self.card_alive.set_value(str(stats.get("alive", 0)))
        self.card_dead.set_value(str(stats.get("dead", 0)))
        self.card_sources.set_value(str(stats.get("sources", 0)))

        by_protocol = stats.get("by_protocol", {})
        max_count = max(by_protocol.values()) if by_protocol else 1
        if max_count == 0:
            max_count = 1

        for protocol, count in by_protocol.items():
            self.protocol_bars[protocol].set(count / max_count)
            self.protocol_labels[protocol].configure(text=str(count))

    def _on_stats_update(self, event: AppEvent) -> None:
        self.after(0, self.refresh)

    def _on_log_entry(self, event: AppEvent) -> None:
        entry = event.data
        self.after(0, lambda: self._append_activity(entry))

    def _append_activity(self, entry) -> None:
        self.activity_text.configure(state="normal")
        ts = entry.timestamp[11:19] if len(entry.timestamp) > 19 else entry.timestamp
        self.activity_text.insert(
            "1.0",
            f"[{ts}] [{entry.level}] {entry.message[:80]}\n"
        )
        self.activity_text.configure(state="disabled")
