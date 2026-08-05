"""Proxy Collector Pro - Main Application Window"""

import customtkinter as ctk
from typing import Dict, Any
from config.constants import (
    APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT, SIDEBAR_WIDTH
)
from config.settings import Settings
from core.database import Database
from gui.pages.dashboard import DashboardPage
from gui.pages.collect import CollectPage
from gui.pages.proxies import ProxiesPage
from gui.pages.sources import SourcesPage
from gui.pages.export import ExportPage
from gui.pages.history import HistoryPage
from gui.pages.logs import LogsPage
from gui.pages.settings import SettingsPage
from utils.logger import get_logger

logger = get_logger()


class ProxyCollectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = Settings.load()
        self.db = Database()

        # Window setup
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Theme
        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("dark-blue")

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_WIDTH, corner_radius=0,
            fg_color=("gray95", "#0f0f23")
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="🔷 Proxy Collector",
            font=("Segoe UI", 16, "bold"),
            text_color=("gray20", "#e0e0ff")
        )
        self.logo_label.pack(
            pady=(20, 30), padx=15, anchor="w"
        )

        # Navigation buttons
        self.pages: Dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        nav_items = [
            ("Dashboard", "📊", DashboardPage),
            ("Collect", "🚀", CollectPage),
            ("Proxies", "🌐", ProxiesPage),
            ("Sources", "📡", SourcesPage),
            ("Export", "📤", ExportPage),
            ("History", "📜", HistoryPage),
            ("Logs", "📝", LogsPage),
            ("Settings", "⚙️", SettingsPage),
        ]

        for name, icon, page_class in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f" {icon} {name}",
                font=("Segoe UI", 12),
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "#1a1a3e"),
                text_color=("gray20", "#cccccc"),
                height=40,
                corner_radius=8,
                command=lambda n=name, p=page_class: (
                    self._show_page(n, p)
                )
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = btn

        # Content frame
        self.content = ctk.CTkFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self.content.grid(
            row=0, column=1, sticky="nsew", padx=5, pady=5
        )
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Status bar
        self.status_bar = ctk.CTkFrame(
            self, height=30, corner_radius=0,
            fg_color=("gray90", "#0a0a1a")
        )
        self.status_bar.grid(
            row=1, column=0, columnspan=2, sticky="ew"
        )
        self.status_bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar, text="Ready",
            font=("Segoe UI", 10),
            text_color=("gray50", "#888888")
        )
        self.status_label.pack(side="left", padx=15, pady=5)

        self.db_label = ctk.CTkLabel(
            self.status_bar, text="● DB: WAL",
            font=("Segoe UI", 10),
            text_color="#27ae60"
        )
        self.db_label.pack(side="right", padx=15, pady=5)

        # Show dashboard by default
        self._show_page("Dashboard", DashboardPage)

        logger.info(
            f"{APP_NAME} v{APP_VERSION} started", "app"
        )

    def _show_page(self, name: str, page_class) -> None:
        # Hide current page
        for page in self.pages.values():
            page.grid_forget()

        # Reset nav button colors
        for btn in self.nav_buttons.values():
            btn.configure(fg_color="transparent")

        # Highlight active
        if name in self.nav_buttons:
            self.nav_buttons[name].configure(
                fg_color=("gray80", "#16213e")
            )

        # Create or show page
        if name not in self.pages:
            if name == "Settings":
                page = page_class(self.content)
            else:
                page = page_class(self.content, self.db)
            self.pages[name] = page
            page.grid(row=0, column=0, sticky="nsew")
        else:
            self.pages[name].grid(
                row=0, column=0, sticky="nsew"
            )
            if hasattr(self.pages[name], "refresh"):
                self.pages[name].refresh()

        self.status_label.configure(text=f"Page: {name}")

    def on_closing(self) -> None:
        self.db.close()
        self.destroy()
