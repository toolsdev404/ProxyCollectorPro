"""Proxy Collector Pro - Logs Page"""

import customtkinter as ctk
from typing import Dict, Any
from tkinter import filedialog
from core.database import Database
from core.events import event_bus, EventType, AppEvent
from utils.logger import get_logger

logger = get_logger()


class LogsPage(ctk.CTkFrame):
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

        self.level_combo = ctk.CTkComboBox(
            self.toolbar,
            values=["ALL", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"],
            command=self._on_level_change,
            width=120
        )
        self.level_combo.set("ALL")
        self.level_combo.pack(side="left", padx=10, pady=10)

        self.refresh_btn = ctk.CTkButton(
            self.toolbar, text="🔄 Refresh",
            command=self.refresh,
            width=100, height=32
        )
        self.refresh_btn.pack(side="left", padx=5, pady=10)

        self.clear_btn = ctk.CTkButton(
            self.toolbar, text="🗑 Clear",
            command=self._clear_logs,
            fg_color="#e74c3c", hover_color="#c0392b",
            width=100, height=32
        )
        self.clear_btn.pack(side="left", padx=5, pady=10)

        self.export_btn = ctk.CTkButton(
            self.toolbar, text="📤 Export",
            command=self._export_logs,
            width=100, height=32
        )
        self.export_btn.pack(side="right", padx=10, pady=10)

        # Log text
        self.log_text = ctk.CTkTextbox(
            self, font=("Consolas", 10), corner_radius=12,
            fg_color=("white", "#0a0a1a")
        )
        self.log_text.grid(
            row=1, column=0, padx=10, pady=10, sticky="nsew"
        )
        self.log_text.configure(state="disabled")

        self.current_level = None
        self.refresh()

        event_bus.subscribe(EventType.LOG_ENTRY, self._on_log_entry)

    def refresh(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")

        entries = self.db.get_logs(
            level=self.current_level, limit=2000
        )
        for entry in entries:
            self.log_text.insert(
                "end",
                f"[{entry.timestamp}] [{entry.level}] {entry.message}\n"
            )

        self.log_text.configure(state="disabled")

    def _on_level_change(self, level: str) -> None:
        self.current_level = level if level != "ALL" else None
        self.refresh()

    def _clear_logs(self) -> None:
        self.db.clear_logs()
        self.refresh()

    def _export_logs(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if path:
            entries = self.db.get_logs(
                level=self.current_level, limit=10000
            )
            with open(path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(
                        f"[{entry.timestamp}] [{entry.level}] "
                        f"{entry.message}\n"
                    )
            logger.success(f"Logs exported to {path}", "gui")

    def _on_log_entry(self, event: AppEvent) -> None:
        self.after(500, self.refresh)
