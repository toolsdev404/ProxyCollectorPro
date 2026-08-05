"""Proxy Collector Pro - Proxies Page"""

import customtkinter as ctk
from typing import Dict, Any, Optional
from gui.components import DataTable, SearchBar, FilterPanel
from core.database import Database
from core.events import event_bus, EventType, AppEvent
from utils.logger import get_logger

logger = get_logger()


class ProxiesPage(ctk.CTkFrame):
    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Search
        self.search = SearchBar(
            self, self._on_search, "Search proxies..."
        )
        self.search.grid(
            row=0, column=0, columnspan=2,
            padx=10, pady=10, sticky="ew"
        )

        # Filters
        self.filter_panel = FilterPanel(
            self,
            {
                "protocol": ["http", "https", "socks4", "socks5"],
                "status": ["alive", "dead", "unchecked"],
                "anonymity": ["elite", "anonymous", "transparent", "unclassified"],
                "country": [],
            },
            self._on_filter
        )
        self.filter_panel.grid(
            row=1, column=0, rowspan=2,
            padx=10, pady=10, sticky="ns"
        )

        # Table
        self.table = DataTable(
            self,
            [
                ("ID", 50), ("Host", 150), ("Port", 60),
                ("Protocol", 80), ("Status", 80), ("Country", 100),
                ("Latency", 70), ("Score", 60), ("Source", 120)
            ],
            on_select=self._on_select
        )
        self.table.grid(
            row=1, column=1, rowspan=2,
            padx=10, pady=10, sticky="nsew"
        )

        # Action buttons
        self.action_frame = ctk.CTkFrame(
            self, fg_color="transparent"
        )
        self.action_frame.grid(
            row=3, column=1, padx=10, pady=10, sticky="e"
        )

        self.refresh_btn = ctk.CTkButton(
            self.action_frame, text="🔄 Refresh",
            command=self.refresh,
            width=100, height=32
        )
        self.refresh_btn.pack(side="left", padx=5)

        self.delete_btn = ctk.CTkButton(
            self.action_frame, text="🗑 Delete",
            command=self._delete_selected,
            fg_color="#e74c3c", hover_color="#c0392b",
            width=100, height=32
        )
        self.delete_btn.pack(side="left", padx=5)

        self.clear_dead_btn = ctk.CTkButton(
            self.action_frame, text="🧹 Clear Dead",
            command=self._clear_dead,
            width=120, height=32
        )
        self.clear_dead_btn.pack(side="left", padx=5)

        self.current_filters: Dict[str, Any] = {}
        self.refresh()

        event_bus.subscribe(
            EventType.STATS_UPDATE,
            lambda e: self.after(1000, self.refresh)
        )

    def refresh(self) -> None:
        proxies = self.db.get_all_proxies(self.current_filters)
        data = []
        for p in proxies[:1000]:
            data.append({
                "id": p.id,
                "host": p.host,
                "port": p.port,
                "protocol": p.protocol,
                "status": p.status,
                "country": p.country or "-",
                "latency": f"{p.latency:.2f}s" if p.latency else "-",
                "score": p.score,
                "source": p.source or "-",
            })
        self.table.set_data(data)

    def _on_search(self, query: str) -> None:
        self.current_filters["search"] = query
        self.refresh()

    def _on_filter(self, filters: Dict[str, str]) -> None:
        self.current_filters.update(filters)
        self.refresh()

    def _on_select(self, row: Dict[str, Any]) -> None:
        logger.info(
            f"Selected proxy: {row.get('host')}:{row.get('port')}",
            "gui"
        )

    def _delete_selected(self) -> None:
        selected = self.table.get_selected()
        if selected and selected.get("id"):
            self.db.delete_proxy(selected["id"])
            self.refresh()

    def _clear_dead(self) -> None:
        count = self.db.delete_dead_proxies()
        logger.info(f"Cleared {count} dead proxies", "gui")
        self.refresh()
