"""Proxy Collector Pro - History Page"""

import customtkinter as ctk
from typing import Dict, Any
from gui.components import DataTable
from core.database import Database
from utils.logger import get_logger

logger = get_logger()


class HistoryPage(ctk.CTkFrame):
    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Toolbar
        self.toolbar = ctk.CTkFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.toolbar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(
            self.toolbar, text="Proxy ID:",
            font=("Segoe UI", 12)
        ).pack(side="left", padx=10, pady=10)
        self.id_entry = ctk.CTkEntry(
            self.toolbar, width=100, height=32
        )
        self.id_entry.pack(side="left", padx=5, pady=10)

        self.load_btn = ctk.CTkButton(
            self.toolbar, text="Load History",
            command=self._load_history,
            width=120, height=32
        )
        self.load_btn.pack(side="left", padx=10, pady=10)

        self.stats_btn = ctk.CTkButton(
            self.toolbar, text="📊 Stats",
            command=self._show_stats,
            width=100, height=32
        )
        self.stats_btn.pack(side="left", padx=5, pady=10)

        # Table
        self.table = DataTable(
            self,
            [
                ("ID", 50), ("Time", 150), ("Event", 100),
                ("Protocol", 80), ("Success", 70),
                ("Latency", 80), ("Endpoint", 200), ("Error", 200)
            ]
        )
        self.table.grid(
            row=1, column=0, padx=10, pady=10, sticky="nsew"
        )

    def _load_history(self) -> None:
        try:
            proxy_id = int(self.id_entry.get())
        except ValueError:
            return

        entries = self.db.get_history_by_proxy(proxy_id, limit=500)
        data = []
        for e in entries:
            data.append({
                "id": e.id,
                "time": e.timestamp[:19] if e.timestamp else "",
                "event": e.event,
                "protocol": e.protocol or "-",
                "success": "Yes" if e.success else "No",
                "latency": f"{e.latency:.2f}s" if e.latency else "-",
                "endpoint": e.endpoint or "-",
                "error": e.error[:50] if e.error else "-",
            })
        self.table.set_data(data)

    def _show_stats(self) -> None:
        try:
            proxy_id = int(self.id_entry.get())
        except ValueError:
            return

        stats = self.db.get_history_stats(proxy_id)

        dialog = ctk.CTkToplevel(self)
        dialog.title("History Statistics")
        dialog.geometry("400x300")
        dialog.transient(self)

        ctk.CTkLabel(
            dialog,
            text=f"Proxy ID: {proxy_id}",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=20)
        ctk.CTkLabel(
            dialog,
            text=f"Total Checks: {stats['total']}",
            font=("Segoe UI", 12)
        ).pack(pady=5)
        ctk.CTkLabel(
            dialog,
            text=f"Successes: {stats['successes']}",
            font=("Segoe UI", 12)
        ).pack(pady=5)
        success_rate = (
            stats['successes'] / stats['total'] * 100
        ) if stats['total'] else 0
        ctk.CTkLabel(
            dialog,
            text=f"Success Rate: {success_rate:.1f}%",
            font=("Segoe UI", 12)
        ).pack(pady=5)
        ctk.CTkLabel(
            dialog,
            text=f"Avg Latency: {stats['avg_latency']}s",
            font=("Segoe UI", 12)
        ).pack(pady=5)
        ctk.CTkLabel(
            dialog,
            text=f"Min Latency: {stats['min_latency']}s",
            font=("Segoe UI", 12)
        ).pack(pady=5)
        ctk.CTkLabel(
            dialog,
            text=f"Max Latency: {stats['max_latency']}s",
            font=("Segoe UI", 12)
        ).pack(pady=5)
