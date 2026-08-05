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

        # Subscribe to new log entries and append incrementally instead of
        # reloading the entire log content on each event to avoid blocking the
        # Tk main thread when logs are emitted rapidly during collection.
        event_bus.subscribe(EventType.LOG_ENTRY, self._on_log_entry)

    def refresh(self) -> None:
        """Reload the most recent logs into the text widget. This is intended
        for manual refreshes or the initial load; frequent automatic updates
        are handled incrementally by _on_log_entry to avoid heavy main-thread work.
        """
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

    def _append_log_entry(self, entry) -> None:
        """Append a single log entry to the text widget on the main thread.
        Filters by current_level when set.
        """
        level = entry.level if hasattr(entry, "level") else getattr(entry, "level", None)
        if self.current_level and level != self.current_level:
            return

        # Insert at end and keep disabled state for read-only display
        self.log_text.configure(state="normal")
        ts = entry.timestamp
        msg = entry.message
        self.log_text.insert("end", f"[{ts}] [{level}] {msg}\n")

        # Optional: keep the widget from growing indefinitely in memory/UI
        # by trimming older lines when exceeding a threshold (2000 lines).
        try:
            # Count lines by indexing 'end-1c' which returns '<line>.<col>'
            last_index = self.log_text.index('end-1c')
            last_line = int(last_index.split('.')[0])
            if last_line > 5000:
                # Delete the earliest 1000 lines to reclaim UI resources.
                self.log_text.delete('1.0', '1000.0')
        except Exception:
            pass

        self.log_text.configure(state="disabled")

    def _on_log_entry(self, event: AppEvent) -> None:
        # Schedule incremental append on the Tk main thread. Avoid calling
        # refresh() here because that reloads up to 2000 entries and blocks the UI.
        entry = event.data
        self.after(0, lambda: self._append_log_entry(entry))
