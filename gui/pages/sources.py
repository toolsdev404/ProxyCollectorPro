"""Proxy Collector Pro - Sources Page"""

import customtkinter as ctk
import threading
from typing import Dict, Any
from gui.components import DataTable
from core.database import Database
from core.models import Source
from core.events import event_bus, EventType, AppEvent
from sources.manager import SourceManager
from utils.logger import get_logger

logger = get_logger()


class SourcesPage(ctk.CTkFrame):
    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db
        self.source_manager = SourceManager(db)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Toolbar
        self.toolbar = ctk.CTkFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.toolbar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.add_btn = ctk.CTkButton(
            self.toolbar, text="+ Add Source",
            command=self._show_add_dialog,
            width=120, height=32
        )
        self.add_btn.pack(side="left", padx=10, pady=10)

        self.test_btn = ctk.CTkButton(
            self.toolbar, text="🧪 Test",
            command=self._test_selected,
            width=100, height=32
        )
        self.test_btn.pack(side="left", padx=5, pady=10)

        self.toggle_btn = ctk.CTkButton(
            self.toolbar, text="Toggle",
            command=self._toggle_selected,
            width=100, height=32
        )
        self.toggle_btn.pack(side="left", padx=5, pady=10)

        self.reset_btn = ctk.CTkButton(
            self.toolbar, text="↺ Reset Built-in",
            command=self._reset_builtin,
            width=130, height=32
        )
        self.reset_btn.pack(side="right", padx=10, pady=10)

        # Table
        self.table = DataTable(
            self,
            [
                ("ID", 50), ("Name", 200), ("URL", 300),
                ("Protocol", 80), ("Enabled", 80),
                ("Priority", 70), ("Health", 80), ("Total", 70)
            ],
            on_select=self._on_select
        )
        self.table.grid(
            row=1, column=0, padx=10, pady=10, sticky="nsew"
        )

        self.refresh()

    def refresh(self) -> None:
        sources = self.source_manager.get_all_sources()
        data = []
        for s in sources:
            data.append({
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "protocol": s.protocol or "all",
                "enabled": "Yes" if s.enabled else "No",
                "priority": s.priority,
                "health": f"{s.health_score:.0f}%",
                "total": s.total_proxies,
            })
        self.table.set_data(data)

    def _on_select(self, row: Dict[str, Any]) -> None:
        self.selected_source = row

    def _show_add_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Source")
        dialog.geometry("500x400")
        dialog.transient(self)

        ctk.CTkLabel(
            dialog, text="Name:", font=("Segoe UI", 12)
        ).pack(anchor="w", padx=20, pady=(20, 5))
        name_entry = ctk.CTkEntry(dialog, width=400)
        name_entry.pack(anchor="w", padx=20)

        ctk.CTkLabel(
            dialog, text="URL:", font=("Segoe UI", 12)
        ).pack(anchor="w", padx=20, pady=(15, 5))
        url_entry = ctk.CTkEntry(dialog, width=400)
        url_entry.pack(anchor="w", padx=20)

        ctk.CTkLabel(
            dialog, text="Protocol:", font=("Segoe UI", 12)
        ).pack(anchor="w", padx=20, pady=(15, 5))
        proto_combo = ctk.CTkComboBox(
            dialog,
            values=["http", "https", "socks4", "socks5", ""],
            width=200
        )
        proto_combo.pack(anchor="w", padx=20)

        ctk.CTkLabel(
            dialog, text="Priority (1-10):", font=("Segoe UI", 12)
        ).pack(anchor="w", padx=20, pady=(15, 5))
        priority_entry = ctk.CTkEntry(dialog, width=100)
        priority_entry.insert(0, "5")
        priority_entry.pack(anchor="w", padx=20)

        def save():
            try:
                source = Source(
                    name=name_entry.get(),
                    url=url_entry.get(),
                    protocol=proto_combo.get(),
                    priority=int(priority_entry.get()),
                    enabled=True,
                    is_custom=True
                )
                if self.source_manager.add_source(source):
                    dialog.destroy()
                    self.refresh()
            except Exception as e:
                logger.error(f"Failed to add source: {e}", "gui")

        ctk.CTkButton(
            dialog, text="Save", command=save, width=100
        ).pack(pady=20)

    def _test_selected(self) -> None:
        selected = self.table.get_selected()
        if not selected:
            return

        source = self.source_manager.db.get_source_by_id(selected["id"])
        if source:
            self.test_btn.configure(state="disabled", text="Testing...")

            def test():
                result = self.source_manager.test_source(source)
                self.after(0, lambda: self._test_done(result))

            threading.Thread(target=test, daemon=True).start()

    def _test_done(self, result: Dict[str, Any]) -> None:
        self.test_btn.configure(state="normal", text="🧪 Test")
        self.refresh()
        logger.info(
            f"Source test: {result.get('source')} - "
            f"{result.get('proxies_found', 0)} proxies",
            "gui"
        )

    def _toggle_selected(self) -> None:
        selected = self.table.get_selected()
        if selected and selected.get("id"):
            self.source_manager.toggle_source(selected["id"])
            self.refresh()

    def _reset_builtin(self) -> None:
        self.source_manager.reset_to_builtin()
        self.refresh()
