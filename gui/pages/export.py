"""Proxy Collector Pro - Export Page"""

import customtkinter as ctk
import os
import threading
from typing import Dict, Any
from tkinter import filedialog
from gui.components import ProgressWidget
from core.database import Database
from core.models import ExportConfig
from core.events import event_bus, EventType, AppEvent
from utils.exporter import ExportEngine
from utils.logger import get_logger

logger = get_logger()


class ExportPage(ctk.CTkFrame):
    def __init__(self, parent, db: Database, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db
        self.exporter = ExportEngine(db)

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Options frame
        self.options_frame = ctk.CTkFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.options_frame.grid(
            row=0, column=0, columnspan=2,
            padx=10, pady=10, sticky="ew"
        )

        # Format
        ctk.CTkLabel(
            self.options_frame, text="Format:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.format_combo = ctk.CTkComboBox(
            self.options_frame,
            values=["txt", "csv", "json"],
            width=100
        )
        self.format_combo.set("txt")
        self.format_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Scheme
        ctk.CTkLabel(
            self.options_frame, text="Scheme:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.scheme_combo = ctk.CTkComboBox(
            self.options_frame,
            values=["with_scheme", "without_scheme", "both"],
            width=150
        )
        self.scheme_combo.set("with_scheme")
        self.scheme_combo.grid(row=0, column=3, padx=10, pady=10, sticky="w")

        # Grouping
        ctk.CTkLabel(
            self.options_frame, text="Grouping:",
            font=("Segoe UI", 12)
        ).grid(row=0, column=4, padx=10, pady=10, sticky="w")
        self.grouping_combo = ctk.CTkComboBox(
            self.options_frame,
            values=["grouped", "separate", "both"],
            width=120
        )
        self.grouping_combo.set("separate")
        self.grouping_combo.grid(row=0, column=5, padx=10, pady=10, sticky="w")

        # Protocols
        ctk.CTkLabel(
            self.options_frame, text="Protocols:",
            font=("Segoe UI", 12)
        ).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.protocol_vars: Dict[str, ctk.CTkCheckBox] = {}
        for i, proto in enumerate(["http", "https", "socks4", "socks5"]):
            var = ctk.CTkCheckBox(
                self.options_frame,
                text=proto.upper(),
                font=("Segoe UI", 11)
            )
            var.select()
            var.grid(row=1, column=i + 1, padx=10, pady=10, sticky="w")
            self.protocol_vars[proto] = var

        # Output path
        ctk.CTkLabel(
            self.options_frame, text="Output:",
            font=("Segoe UI", 12)
        ).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.output_entry = ctk.CTkEntry(
            self.options_frame, width=400
        )
        self.output_entry.grid(
            row=2, column=1, columnspan=4,
            padx=10, pady=10, sticky="ew"
        )

        self.browse_btn = ctk.CTkButton(
            self.options_frame, text="Browse...",
            command=self._browse,
            width=100, height=32
        )
        self.browse_btn.grid(row=2, column=5, padx=10, pady=10)

        # Export button
        self.export_btn = ctk.CTkButton(
            self, text="📤 Export Now",
            font=("Segoe UI", 14, "bold"),
            command=self._export,
            fg_color="#3498db", hover_color="#2980b9",
            height=45, corner_radius=12
        )
        self.export_btn.grid(
            row=1, column=0, columnspan=2,
            padx=10, pady=20
        )

        # Progress
        self.progress = ProgressWidget(self, "Export Progress")
        self.progress.grid(
            row=2, column=0, columnspan=2,
            padx=10, pady=10, sticky="ew"
        )

    def _browse(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def _export(self) -> None:
        protocols = [
            p for p, var in self.protocol_vars.items() if var.get()
        ]

        config = ExportConfig(
            format=self.format_combo.get(),
            scheme=self.scheme_combo.get(),
            grouping=self.grouping_combo.get(),
            protocols=protocols,
            output_path=self.output_entry.get() or None
        )

        self.export_btn.configure(state="disabled", text="Exporting...")
        self.progress.set_status("Exporting...")

        def do_export():
            result = self.exporter.export(config)
            self.after(0, lambda: self._export_done(result))

        threading.Thread(target=do_export, daemon=True).start()

    def _export_done(self, result: Dict[str, Any]) -> None:
        self.export_btn.configure(state="normal", text="📤 Export Now")

        if result["success"]:
            files = result.get("files", [])
            self.progress.set_progress(
                1.0,
                f"Exported {result['total']} proxies to "
                f"{len(files)} file(s)"
            )
            logger.success(f"Export complete: {files}", "gui")
        else:
            self.progress.set_status(
                f"Export failed: {result.get('error', 'Unknown error')}"
            )
            logger.error(
                f"Export failed: {result.get('error')}", "gui"
            )
