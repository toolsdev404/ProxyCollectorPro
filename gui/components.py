"""Proxy Collector Pro - GUI Reusable Components"""

import customtkinter as ctk
from typing import Callable, List, Dict, Any, Optional, Tuple
from config.constants import (
    DARK_BG, DARK_CARD, DARK_ACCENT, DARK_TEXT,
    LIGHT_BG, LIGHT_CARD, LIGHT_ACCENT, LIGHT_TEXT,
    TABLE_ROW_HEIGHT
)

class StatCard(ctk.CTkFrame):
    def __init__(self, parent, title: str, value: str = "0", subtitle: str = "", 
                 icon: str = "", color: str = "#3498db", **kwargs):
        super().__init__(parent, fg_color=(LIGHT_CARD, DARK_CARD), corner_radius=12, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        # Icon label
        if icon:
            self.icon_label = ctk.CTkLabel(
                self, text=icon, font=("Segoe UI", 24),
                text_color=color
            )
            self.icon_label.grid(row=0, column=0, padx=15, pady=(15, 0), sticky="w")

        # Value label
        self.value_label = ctk.CTkLabel(
            self, text=value, font=("Segoe UI", 32, "bold"),
            text_color=(LIGHT_TEXT, "#ffffff")
        )
        self.value_label.grid(row=1, column=0, padx=15, pady=(5, 0), sticky="w")

        # Title label
        self.title_label = ctk.CTkLabel(
            self, text=title, font=("Segoe UI", 12),
            text_color=("#666666", "#aaaaaa")
        )
        self.title_label.grid(row=2, column=0, padx=15, pady=(0, 5), sticky="w")

        # Subtitle
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self, text=subtitle, font=("Segoe UI", 10),
                text_color=("#999999", "#888888")
            )
            self.subtitle_label.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")

    def set_value(self, value: str) -> None:
        self.value_label.configure(text=value)

class DataTable(ctk.CTkFrame):
    def __init__(self, parent, columns: List[Tuple[str, int]], 
                 on_select: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.columns = columns
        self.on_select = on_select
        self.rows: List[Dict[str, Any]] = []
        self.selected_index: Optional[int] = None

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color=(LIGHT_ACCENT, DARK_ACCENT), corner_radius=0, height=35)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_propagate(False)

        for i, (col_name, col_width) in enumerate(columns):
            lbl = ctk.CTkLabel(
                self.header_frame, text=col_name, font=("Segoe UI", 11, "bold"),
                text_color="#ffffff", width=col_width
            )
            lbl.grid(row=0, column=i, padx=5, pady=5)

        # Scrollable body
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.row_frames: List[ctk.CTkFrame] = []

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        # Clear existing rows
        for frame in self.row_frames:
            frame.destroy()
        self.row_frames = []
        self.rows = data

        for idx, row_data in enumerate(data):
            row_frame = ctk.CTkFrame(
                self.scroll_frame, 
                fg_color=("#f0f0f0", "#2a2a4a") if idx % 2 == 0 else ("#ffffff", "#1a1a3e"),
                corner_radius=0,
                height=TABLE_ROW_HEIGHT
            )
            row_frame.grid(row=idx, column=0, sticky="ew", pady=1)
            row_frame.grid_propagate(False)
            row_frame.bind("<Button-1>", lambda e, i=idx: self._on_row_click(i))

            for col_idx, (col_name, col_width) in enumerate(self.columns):
                key = col_name.lower().replace(" ", "_")
                value = str(row_data.get(key, ""))

                # Truncate long values
                if len(value) > 30:
                    value = value[:27] + "..."

                lbl = ctk.CTkLabel(
                    row_frame, text=value, font=("Segoe UI", 10),
                    width=col_width, anchor="w"
                )
                lbl.grid(row=0, column=col_idx, padx=5, pady=2)
                lbl.bind("<Button-1>", lambda e, i=idx: self._on_row_click(i))

            self.row_frames.append(row_frame)

    def _on_row_click(self, index: int) -> None:
        if self.selected_index is not None and self.selected_index < len(self.row_frames):
            old_frame = self.row_frames[self.selected_index]
            old_frame.configure(fg_color=("#f0f0f0", "#2a2a4a") if self.selected_index % 2 == 0 else ("#ffffff", "#1a1a3e"))

        self.selected_index = index
        if index < len(self.row_frames):
            self.row_frames[index].configure(fg_color=("#d0e8ff", "#0f3460"))

        if self.on_select and index < len(self.rows):
            self.on_select(self.rows[index])

    def get_selected(self) -> Optional[Dict[str, Any]]:
        if self.selected_index is not None and self.selected_index < len(self.rows):
            return self.rows[self.selected_index]
        return None

    def clear_selection(self) -> None:
        if self.selected_index is not None and self.selected_index < len(self.row_frames):
            old_frame = self.row_frames[self.selected_index]
            old_frame.configure(fg_color=("#f0f0f0", "#2a2a4a") if self.selected_index % 2 == 0 else ("#ffffff", "#1a1a3e"))
        self.selected_index = None

class SearchBar(ctk.CTkFrame):
    def __init__(self, parent, on_search: Callable, placeholder: str = "Search...", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.entry = ctk.CTkEntry(
            self, placeholder_text=placeholder,
            font=("Segoe UI", 12), height=35,
            corner_radius=8
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.grid_columnconfigure(0, weight=1)

        self.search_btn = ctk.CTkButton(
            self, text="🔍 Search", font=("Segoe UI", 11),
            command=lambda: on_search(self.entry.get()),
            width=100, height=35, corner_radius=8
        )
        self.search_btn.grid(row=0, column=1)

        self.entry.bind("<Return>", lambda e: on_search(self.entry.get()))

class FilterPanel(ctk.CTkFrame):
    def __init__(self, parent, filters: Dict[str, List[str]], on_filter: Callable, **kwargs):
        super().__init__(parent, fg_color=(LIGHT_CARD, DARK_CARD), corner_radius=12, **kwargs)

        self.filters = filters
        self.on_filter = on_filter
        self.controls: Dict[str, Any] = {}

        row = 0
        for filter_name, options in filters.items():
            lbl = ctk.CTkLabel(
                self, text=filter_name.replace("_", " ").title(),
                font=("Segoe UI", 11, "bold")
            )
            lbl.grid(row=row, column=0, padx=10, pady=(10, 5), sticky="w")
            row += 1

            combo = ctk.CTkComboBox(
                self, values=["All"] + options,
                font=("Segoe UI", 11), height=30,
                command=lambda val, fn=filter_name: self._on_change(fn, val)
            )
            combo.set("All")
            combo.grid(row=row, column=0, padx=10, pady=(0, 10), sticky="ew")
            self.controls[filter_name] = combo
            row += 1

        self.grid_columnconfigure(0, weight=1)

    def _on_change(self, filter_name: str, value: str) -> None:
        result = {}
        for name, control in self.controls.items():
            val = control.get()
            if val and val != "All":
                result[name] = val
        self.on_filter(result)

    def reset(self) -> None:
        for control in self.controls.values():
            control.set("All")
        self.on_filter({})

class StatusBadge(ctk.CTkLabel):
    COLORS = {
        "alive": ("#27ae60", "#00d9ff"),
        "dead": ("#e74c3c", "#e74c3c"),
        "unchecked": ("#f39c12", "#f39c12"),
        "checking": ("#3498db", "#3498db"),
        "elite": ("#9b59b6", "#bb8fce"),
        "anonymous": ("#3498db", "#5dade2"),
        "transparent": ("#e67e22", "#f0b27a"),
    }

    def __init__(self, parent, status: str, **kwargs):
        color = self.COLORS.get(status.lower(), ("#95a5a6", "#95a5a6"))
        super().__init__(
            parent, text=status.upper(),
            font=("Segoe UI", 9, "bold"),
            text_color="#ffffff",
            fg_color=color[0],
            corner_radius=12,
            width=80, height=22,
            **kwargs
        )

class ProgressWidget(ctk.CTkFrame):
    def __init__(self, parent, title: str = "Progress", **kwargs):
        super().__init__(parent, fg_color=(LIGHT_CARD, DARK_CARD), corner_radius=12, **kwargs)

        self.title_label = ctk.CTkLabel(
            self, text=title, font=("Segoe UI", 12, "bold")
        )
        self.title_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.progress = ctk.CTkProgressBar(self, height=8, corner_radius=4)
        self.progress.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            self, text="Ready", font=("Segoe UI", 10),
            text_color=("#666666", "#aaaaaa")
        )
        self.status_label.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="w")

        self.grid_columnconfigure(0, weight=1)

    def set_progress(self, value: float, status: str = "") -> None:
        self.progress.set(min(1.0, max(0.0, value)))
        if status:
            self.status_label.configure(text=status)

    def set_status(self, status: str) -> None:
        self.status_label.configure(text=status)
