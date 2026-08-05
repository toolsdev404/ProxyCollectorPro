"""Proxy Collector Pro - Settings Page"""

import customtkinter as ctk
import threading
from typing import Dict, Any
from config.settings import Settings
from config.constants import Preset
from utils.logger import get_logger
from utils.diagnostics import Diagnostics

logger = get_logger()


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.settings = Settings.load()

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel
        self.left_panel = ctk.CTkScrollableFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.left_panel.grid(
            row=0, column=0, padx=10, pady=10, sticky="nsew"
        )

        # General
        ctk.CTkLabel(
            self.left_panel, text="General",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.theme_var = ctk.StringVar(value=self.settings.theme)
        ctk.CTkLabel(
            self.left_panel, text="Theme:",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=15)
        self.theme_combo = ctk.CTkComboBox(
            self.left_panel,
            values=["dark", "light"],
            variable=self.theme_var,
            width=200
        )
        self.theme_combo.pack(anchor="w", padx=15, pady=(0, 15))

        # Collection
        ctk.CTkLabel(
            self.left_panel, text="Collection",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            self.left_panel, text="Threads:",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=15)
        self.threads_entry = ctk.CTkEntry(
            self.left_panel, width=200
        )
        self.threads_entry.insert(0, str(self.settings.threads))
        self.threads_entry.pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            self.left_panel, text="Timeout (seconds):",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=15)
        self.timeout_entry = ctk.CTkEntry(
            self.left_panel, width=200
        )
        self.timeout_entry.insert(0, str(self.settings.timeout))
        self.timeout_entry.pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            self.left_panel, text="Max Retries:",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=15)
        self.retries_entry = ctk.CTkEntry(
            self.left_panel, width=200
        )
        self.retries_entry.insert(0, str(self.settings.max_retries))
        self.retries_entry.pack(anchor="w", padx=15, pady=(0, 15))

        # Targets
        ctk.CTkLabel(
            self.left_panel, text="Default Targets",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.target_entries: Dict[str, ctk.CTkEntry] = {}
        for protocol in ["HTTP", "HTTPS", "SOCKS4", "SOCKS5"]:
            ctk.CTkLabel(
                self.left_panel, text=f"{protocol}:",
                font=("Segoe UI", 11)
            ).pack(anchor="w", padx=15)
            entry = ctk.CTkEntry(
                self.left_panel, width=200
            )
            default = getattr(
                self.settings,
                f"target_{protocol.lower()}",
                100
            )
            entry.insert(0, str(default))
            entry.pack(anchor="w", padx=15, pady=(0, 10))
            self.target_entries[protocol.lower()] = entry

        # Right panel
        self.right_panel = ctk.CTkScrollableFrame(
            self, fg_color=("white", "#16213e"), corner_radius=12
        )
        self.right_panel.grid(
            row=0, column=1, padx=10, pady=10, sticky="nsew"
        )

        # GeoIP
        ctk.CTkLabel(
            self.right_panel, text="GeoIP",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.geoip_var = ctk.BooleanVar(
            value=self.settings.geoip_enabled
        )
        self.geoip_check = ctk.CTkCheckBox(
            self.right_panel,
            text="Enable GeoIP resolution",
            variable=self.geoip_var,
            font=("Segoe UI", 11)
        )
        self.geoip_check.pack(anchor="w", padx=15, pady=(0, 15))

        # Export
        ctk.CTkLabel(
            self.right_panel, text="Export",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            self.right_panel, text="Default Format:",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=15)
        self.format_combo = ctk.CTkComboBox(
            self.right_panel,
            values=["txt", "csv", "json"],
            width=200
        )
        self.format_combo.set(self.settings.default_export_format)
        self.format_combo.pack(anchor="w", padx=15, pady=(0, 15))

        # Logging
        ctk.CTkLabel(
            self.right_panel, text="Logging",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            self.right_panel, text="Log Level:",
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=15)
        self.log_level_combo = ctk.CTkComboBox(
            self.right_panel,
            values=["DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR"],
            width=200
        )
        self.log_level_combo.set(self.settings.log_level)
        self.log_level_combo.pack(anchor="w", padx=15, pady=(0, 15))

        # Diagnostics
        ctk.CTkLabel(
            self.right_panel, text="Diagnostics",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.diag_btn = ctk.CTkButton(
            self.right_panel,
            text="🔍 Run Diagnostics",
            command=self._run_diagnostics,
            width=200, height=35
        )
        self.diag_btn.pack(anchor="w", padx=15, pady=(0, 15))

        self.diag_text = ctk.CTkTextbox(
            self.right_panel, height=200,
            font=("Consolas", 10)
        )
        self.diag_text.pack(
            fill="x", padx=15, pady=(0, 15)
        )
        self.diag_text.configure(state="disabled")

        # Save button
        self.save_btn = ctk.CTkButton(
            self, text="💾 Save Settings",
            font=("Segoe UI", 14, "bold"),
            command=self._save_settings,
            fg_color="#27ae60", hover_color="#1e8449",
            height=45, corner_radius=12
        )
        self.save_btn.grid(
            row=1, column=0, columnspan=2,
            padx=10, pady=20
        )

    def _save_settings(self) -> None:
        try:
            self.settings.theme = self.theme_var.get()
            self.settings.threads = int(self.threads_entry.get())
            self.settings.timeout = int(self.timeout_entry.get())
            self.settings.max_retries = int(self.retries_entry.get())
            self.settings.geoip_enabled = self.geoip_var.get()
            self.settings.default_export_format = (
                self.format_combo.get()
            )
            self.settings.log_level = self.log_level_combo.get()

            for protocol, entry in self.target_entries.items():
                setattr(
                    self.settings,
                    f"target_{protocol}",
                    int(entry.get())
                )

            self.settings.save()
            logger.success("Settings saved", "gui")

            # Apply theme
            ctk.set_appearance_mode(self.settings.theme)

        except Exception as e:
            logger.error(f"Failed to save settings: {e}", "gui")

    def _run_diagnostics(self) -> None:
        self.diag_text.configure(state="normal")
        self.diag_text.delete("1.0", "end")
        self.diag_text.insert(
            "end", "Running diagnostics...\n\n"
        )
        self.diag_text.configure(state="disabled")

        def run():
            results = Diagnostics.run_all()
            self.after(0, lambda: self._show_diagnostics(results))

        threading.Thread(target=run, daemon=True).start()

    def _show_diagnostics(self, results) -> None:
        self.diag_text.configure(state="normal")
        self.diag_text.delete("1.0", "end")

        for r in results:
            icon = (
                "✅" if r.status == "ok"
                else "⚠️" if r.status == "warning"
                else "❌"
            )
            self.diag_text.insert(
                "end",
                f"{icon} {r.name}: {r.message}\n"
            )
            if r.details:
                for key, val in r.details.items():
                    self.diag_text.insert(
                        "end",
                        f"   └─ {key}: {val}\n"
                    )

        self.diag_text.configure(state="disabled")
