"""Native CustomTkinter dashboard backed by read-only repository queries."""

from __future__ import annotations

import queue
import threading
import time
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from file_management import exporters
from storage import repositories

POLL_INTERVAL_SECONDS = 2.0
VIEW_NAMES = ("Overview", "Traffic", "Occupancy", "Queue", "Shelf", "Alerts", "Reports")


def _display_time(value: object) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else str(value)


def _hourly_traffic() -> list[tuple[str, int, int]]:
    current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    boundaries = [current_hour - timedelta(hours=offset) for offset in range(24, -1, -1)]
    totals = [repositories.entry_exit_counts(since=boundary) for boundary in boundaries]
    buckets = []
    for index, start in enumerate(boundaries[:-1]):
        buckets.append(
            (
                start.astimezone().strftime("%H:%M"),
                totals[index]["in"] - totals[index + 1]["in"],
                totals[index]["out"] - totals[index + 1]["out"],
            )
        )
    return buckets


class DataPoller(threading.Thread):
    """Collect data off the UI thread; it never touches a Tk widget."""

    def __init__(self, updates: queue.Queue[dict], stop_event: threading.Event):
        super().__init__(daemon=True)
        self.updates = updates
        self.stop_event = stop_event

    def run(self) -> None:
        traffic = []
        traffic_refreshed_at = 0.0
        while not self.stop_event.is_set():
            try:
                if time.monotonic() - traffic_refreshed_at >= 10.0:
                    traffic = _hourly_traffic()
                    traffic_refreshed_at = time.monotonic()
                self.updates.put({
                    "entry_exit": repositories.entry_exit_counts(),
                    "cameras": repositories.list_cameras(),
                    "traffic": traffic,
                    "occupancy": repositories.recent_occupancy(limit=100),
                    "queue": repositories.recent_queue_metrics(limit=100),
                    "shelf": repositories.recent_shelf_events(limit=50),
                    "alerts": repositories.active_alerts(),
                    "events": repositories.recent_events(limit=100),
                })
            except Exception as error:
                self.updates.put({"error": str(error)})
            self.stop_event.wait(POLL_INTERVAL_SECONDS)


class Dashboard(ctk.CTk):
    def __init__(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.theme_mode = "Dark"
        ctk.set_appearance_mode(self.theme_mode)
        self.title("Retail Intelligence Platform")
        self.geometry("1280x780")
        self.minsize(980, 620)
        self.updates: queue.Queue[dict] = queue.Queue()
        self.stop_event = threading.Event()
        self.snapshot: dict = {}
        self.views: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.current_view = "Overview"
        self.theme_transitioning = False
        self._build_shell()
        self._show_view("Overview")
        self.poller = DataPoller(self.updates, self.stop_event)
        self.poller.start()
        self.after(100, self._consume_updates)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=("#102033", "#091521"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        ctk.CTkLabel(sidebar, text="RETAIL INTELLIGENCE", text_color="#f8fafc", font=ctk.CTkFont(size=18, weight="bold")).pack(
            padx=20, pady=(28, 4), anchor="w"
        )
        ctk.CTkLabel(sidebar, text="LOCAL OPERATIONS", text_color="#7dd3fc").pack(
            padx=20, pady=(0, 24), anchor="w"
        )
        for name in VIEW_NAMES:
            button = ctk.CTkButton(
                sidebar, text=name, anchor="w", height=40, corner_radius=7,
                fg_color="transparent", hover_color="#1e3a52", text_color="#cbd5e1",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda view_name=name: self._show_view(view_name),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[name] = button
        self.theme_button = ctk.CTkButton(
            sidebar, text="USE BRIGHT THEME", height=34, corner_radius=7,
            fg_color="#164e63", hover_color="#1e7490", font=ctk.CTkFont(size=11, weight="bold"), command=self._toggle_theme,
        )
        self.theme_button.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        self.status_label = ctk.CTkLabel(sidebar, text="CONNECTING...", text_color="#fbbf24", anchor="w", wraplength=190, font=ctk.CTkFont(size=11, weight="bold"))
        self.status_label.pack(side="bottom", fill="x", padx=20, pady=20)
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("#eef3f7", "#111c28"))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(self.content, text="Overview", font=ctk.CTkFont(size=28, weight="bold"))
        self.page_title.grid(row=0, column=0, sticky="w", padx=24, pady=(28, 18))

    def _show_view(self, name: str) -> None:
        self.current_view = name
        for view in self.views.values():
            view.grid_forget()
        if name not in self.views:
            self.views[name] = self._create_view(name)
        self.page_title.configure(text=name)
        for view_name, button in self.nav_buttons.items():
            button.configure(
                fg_color="#155e75" if view_name == name else "transparent",
                text_color="#ffffff" if view_name == name else "#cbd5e1",
            )
        self.views[name].grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self._render_view(name)

    def _create_view(self, name: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        if name in {"Traffic", "Occupancy", "Queue"}:
            frame.chart = self._make_chart(frame)
            detail_columns = {
                "Traffic": ("Hour", "In", "Out", "Total"),
                "Occupancy": ("Time", "Zone", "People"),
                "Queue": ("Time", "Zone", "Queue", "Wait (sec)"),
            }[name]
            frame.detail_table = self._make_table(frame, detail_columns, row=1)
            frame.grid_rowconfigure(0, weight=3)
            frame.grid_rowconfigure(1, weight=2)
        elif name == "Reports":
            self._build_reports(frame)
        elif name == "Overview":
            frame.kpis = self._make_kpis(frame)
            frame.grid_rowconfigure(1, weight=0)
            frame.grid_rowconfigure(2, weight=1)
            frame.camera_panel = self._make_camera_panel(frame)
            frame.camera_panel.grid(row=1, column=0, sticky="ew", pady=(0, 14))
            frame.table = self._make_table(frame, ("Type", "Severity", "Zone", "Message", "Time"), row=2)
        elif name == "Alerts":
            frame.table = self._make_table(frame, ("Severity", "Message", "Zone", "Status", "Created"))
        else:
            frame.table = self._make_table(frame, ("Camera", "Zone", "Activity", "Time"))
        return frame

    def _toggle_theme(self) -> None:
        if self.theme_transitioning:
            return
        self.theme_transitioning = True
        self.theme_button.configure(state="disabled", text="UPDATING THEME...")
        self.theme_mode = "Light" if self.theme_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(self.theme_mode)
        self.after(80, self._finish_theme_transition)

    def _finish_theme_transition(self) -> None:
        self._apply_table_theme()
        self._render_view(self.current_view)
        self.theme_button.configure(
            state="normal",
            text="USE DARK THEME" if self.theme_mode == "Light" else "USE BRIGHT THEME",
        )
        self.theme_transitioning = False

    def _chart_name(self, frame: ctk.CTkFrame) -> str:
        for name, candidate in self.views.items():
            if candidate is frame:
                return name
        return "Traffic"

    def _apply_table_theme(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        dark = self.theme_mode == "Dark"
        background = "#172737" if dark else "#ffffff"
        foreground = "#e2e8f0" if dark else "#17202a"
        heading = "#23415a" if dark else "#dbe7f0"
        style.configure("Dashboard.Treeview", rowheight=30, font=("Segoe UI", 10, "bold"), background=background, fieldbackground=background, foreground=foreground)
        style.configure("Dashboard.Treeview.Heading", font=("Segoe UI", 10, "bold"), background=heading, foreground="#f8fafc" if dark else "#17324d")
        style.map("Dashboard.Treeview", background=[("selected", "#155e75")], foreground=[("selected", "#ffffff")])

    def _make_camera_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent, corner_radius=10, border_width=1, border_color=("#d5dee8", "#29465d"), fg_color=("#ffffff", "#172737"))
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(panel, text="Camera health", anchor="w", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 2)
        )
        panel.summary_label = ctk.CTkLabel(panel, text="Waiting for camera status...", anchor="w", text_color=("#64748b", "#9fb3c5"), font=ctk.CTkFont(size=11, weight="bold"))
        panel.summary_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 2))
        ctk.CTkLabel(panel, text="Each registered camera keeps a stable status card for future hardware feeds.", anchor="w", text_color=("#64748b", "#9fb3c5"), font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=16, pady=(0, 10)
        )
        panel.rows = ctk.CTkFrame(panel, fg_color="transparent")
        panel.rows.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        panel.camera_rows = {}
        panel.camera_ids = None
        return panel

    def _make_kpis(self, parent: ctk.CTkFrame) -> list[ctk.CTkLabel]:
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        labels: list[ctk.CTkLabel] = []
        for column, title in enumerate(("Today's footfall", "Average queue", "Alerts fired")):
            holder.grid_columnconfigure(column, weight=1)
            card = ctk.CTkFrame(
                holder, corner_radius=10, border_width=1,
                border_color=("#d5dee8", "#26384a"), fg_color=("#ffffff", "#172737"),
            )
            card.grid(row=0, column=column, sticky="ew", padx=(0, 12))
            ctk.CTkLabel(card, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", padx=18, pady=(14, 0))
            value = ctk.CTkLabel(card, text="-", anchor="w", font=ctk.CTkFont(size=28, weight="bold"))
            value.pack(fill="x", padx=18, pady=(2, 14))
            labels.append(value)
        return labels

    def _make_chart(self, parent: ctk.CTkFrame) -> FigureCanvasTkAgg:
        figure = Figure(figsize=(8, 4), dpi=100)
        canvas = FigureCanvasTkAgg(figure, master=parent)
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        parent.grid_rowconfigure(0, weight=1)
        parent.chart_axis = figure.add_subplot(111)
        return canvas

    def _make_table(self, parent: ctk.CTkFrame, columns: tuple[str, ...], row: int = 1) -> ttk.Treeview:
        style = ttk.Style()
        style.configure("Dashboard.Treeview", rowheight=30, font=("Segoe UI", 10, "bold"), background="#ffffff", fieldbackground="#ffffff", foreground="#17202a")
        style.configure("Dashboard.Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#dbe7f0", foreground="#17324d")
        style.map("Dashboard.Treeview", background=[("selected", "#bae6fd")], foreground=[("selected", "#0c2940")])
        self._apply_table_theme()
        table = ttk.Treeview(parent, columns=columns, show="headings")
        table.configure(style="Dashboard.Treeview")
        for column in columns:
            table.heading(column, text=column)
            table.column(column, width=150, anchor="w")
        table.grid(row=row, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
        scrollbar.grid(row=row, column=1, sticky="ns")
        table.configure(yscrollcommand=scrollbar.set)
        return table

    def _build_reports(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="Export center", anchor="w", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(8, 2)
        )
        ctk.CTkLabel(parent, text="Create manager-ready snapshots from the current local database.", anchor="w", text_color=("#64748b", "#9fb3c5"), font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )
        export_rows = (
            ("Queue metrics", exporters.export_queue_metrics),
            ("Occupancy", exporters.export_occupancy),
            ("Active alerts", exporters.export_alerts),
            ("Recent events", exporters.export_events),
        )
        for row, (label, function) in enumerate(export_rows, start=2):
            ctk.CTkLabel(parent, text=label, anchor="w", font=ctk.CTkFont(size=13, weight="bold")).grid(row=row, column=0, padx=(0, 22), pady=8, sticky="w")
            ctk.CTkButton(parent, text="SAVE CSV", width=112, height=34, corner_radius=7, command=lambda fn=function: self._export(fn, "csv")).grid(row=row, column=1, padx=5, pady=8)
            ctk.CTkButton(parent, text="SAVE JSON", width=112, height=34, corner_radius=7, command=lambda fn=function: self._export(fn, "json")).grid(row=row, column=2, padx=5, pady=8)
        self.export_status = ctk.CTkLabel(parent, text="Exports are saved under data/exports.", anchor="w", wraplength=700, font=ctk.CTkFont(size=12, weight="bold"))
        self.export_status.grid(row=6, column=0, columnspan=2, sticky="w", pady=(18, 8))
        ctk.CTkButton(parent, text="OPEN EXPORT FOLDER", width=180, height=34, corner_radius=7, command=self._open_export_folder).grid(row=6, column=2, padx=5, pady=(18, 8), sticky="e")

    def _export(self, function, fmt: str) -> None:
        try:
            path = function(fmt=fmt)
            self.last_export_path = Path(path).resolve()
            self.export_status.configure(text=f"Saved {self.last_export_path.name}\nLocation: {self.last_export_path}", text_color="#4ade80")
        except Exception as error:
            self.export_status.configure(text=f"Export failed: {error}", text_color="#fb7185")

    def _open_export_folder(self) -> None:
        folder = getattr(self, "last_export_path", Path("data/exports").resolve())
        target = folder if folder.is_dir() else folder.parent
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(str(target))

    def _consume_updates(self) -> None:
        try:
            while True:
                self.snapshot = self.updates.get_nowait()
        except queue.Empty:
            pass
        if self.snapshot:
            if "error" in self.snapshot:
                self.status_label.configure(text=f"DATABASE OFFLINE\n{self.snapshot['error']}", text_color="#fb7185")
            else:
                cameras = self.snapshot.get("cameras", [])
                online = sum(1 for camera in cameras if camera.online)
                self.status_label.configure(
                    text=f"LIVE  {datetime.now().strftime('%H:%M:%S')}\nCAMERAS  {online}/{len(cameras)} ONLINE",
                    text_color="#86efac",
                )
                self._render_view(self.current_view)
        self.after(250, self._consume_updates)

    def _render_view(self, name: str) -> None:
        if not self.snapshot or "error" in self.snapshot or name == "Reports":
            return
        frame = self.views[name]
        if name == "Overview":
            counts = self.snapshot["entry_exit"]
            queue_rows = self.snapshot["queue"]
            average = sum(row.queue_length for row in queue_rows) / len(queue_rows) if queue_rows else 0
            frame.kpis[0].configure(text=str(counts.get("in", 0) + counts.get("out", 0)))
            frame.kpis[1].configure(text=f"{average:.1f}")
            frame.kpis[2].configure(text=str(len(self.snapshot["alerts"])))
            self._render_camera_panel(frame.camera_panel, self.snapshot["cameras"])
            self._fill(frame.table, [(e.event_type, e.severity, e.zone_id or "-", e.message, _display_time(e.timestamp)) for e in self.snapshot["events"][:30]])
        elif name == "Alerts":
            self._fill(frame.table, [(a.severity, a.message, a.zone_id or "-", a.status, _display_time(a.created_at)) for a in self.snapshot["alerts"]])
        elif name == "Shelf":
            self._fill(frame.table, [(e.camera_id, e.zone_id or "-", e.event_label, _display_time(e.timestamp)) for e in self.snapshot["shelf"]])
        elif name in {"Traffic", "Occupancy", "Queue"}:
            self._render_detail_table(frame, name)
            self._render_chart(frame, name)

    def _fill(self, table: ttk.Treeview, rows: list[tuple]) -> None:
        table.delete(*table.get_children())
        for row in rows:
            table.insert("", "end", values=row)

    def _render_camera_panel(self, panel: ctk.CTkFrame, cameras: list) -> None:
        online_count = sum(1 for camera in cameras if camera.online)
        panel.summary_label.configure(text=f"{online_count} online  /  {len(cameras)} registered  •  refreshed {datetime.now().strftime('%H:%M:%S')}")
        camera_ids = tuple(camera.id for camera in cameras)
        if camera_ids != panel.camera_ids:
            for child in panel.rows.winfo_children():
                child.destroy()
            panel.camera_rows = {}
            panel.camera_ids = camera_ids
            if not cameras:
                panel.empty_label = ctk.CTkLabel(panel.rows, text="No cameras registered", text_color=("#64748b", "#9fb3c5"))
                panel.empty_label.pack(anchor="w", padx=8, pady=8)
                return
            for index, camera in enumerate(cameras):
                panel.rows.grid_columnconfigure(index, weight=1)
                card = ctk.CTkFrame(panel.rows, corner_radius=8, border_width=1, border_color=("#e2e8f0", "#29465d"), fg_color=("#f8fafc", "#1d3346"))
                card.grid(row=0, column=index, sticky="ew", padx=4, pady=2)
                connected = ctk.BooleanVar(value=bool(camera.online))
                checkbox = ctk.CTkCheckBox(card, text="", variable=connected, state="disabled", width=24, checkbox_width=20, checkbox_height=20, fg_color="#22c55e", hover_color="#22c55e")
                checkbox.pack(side="left", padx=(10, 2), pady=10)
                details = ctk.CTkFrame(card, fg_color="transparent")
                details.pack(side="left", fill="x", expand=True, padx=(2, 8), pady=7)
                name_label = ctk.CTkLabel(details, text=camera.label, anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
                name_label.pack(fill="x")
                state_label = ctk.CTkLabel(details, anchor="w", font=ctk.CTkFont(size=11, weight="bold"))
                state_label.pack(fill="x")
                seen_label = ctk.CTkLabel(details, anchor="w", text_color=("#64748b", "#9fb3c5"), font=ctk.CTkFont(size=10, weight="bold"))
                seen_label.pack(fill="x")
                panel.camera_rows[camera.id] = (connected, checkbox, name_label, state_label, seen_label)
        for camera in cameras:
            connected, checkbox, name_label, state_label, seen_label = panel.camera_rows[camera.id]
            connected.set(bool(camera.online))
            checkbox.configure(fg_color="#22c55e" if camera.online else "#64748b")
            name_label.configure(text=camera.label)
            state = "ONLINE" if camera.online else "OFFLINE"
            state_label.configure(text=f"{state}  •  {camera.zone_id or 'Unassigned'}", text_color="#4ade80" if camera.online else "#fb7185")
            seen_label.configure(text=f"Seen {_display_time(camera.last_seen or 'Never')}")

    def _render_detail_table(self, frame: ctk.CTkFrame, name: str) -> None:
        if name == "Traffic":
            rows = [(hour, incoming, outgoing, incoming + outgoing) for hour, incoming, outgoing in self.snapshot["traffic"]]
        elif name == "Occupancy":
            occupancy = list(reversed(self.snapshot["occupancy"]))
            rows = [(_display_time(metric.timestamp), metric.zone_id or "-", metric.current_count) for metric in occupancy]
        else:
            queue_rows = list(reversed(self.snapshot["queue"]))
            rows = [
                (_display_time(metric.timestamp), metric.zone_id or "-", metric.queue_length, f"{metric.avg_wait_seconds or 0:.0f}")
                for metric in queue_rows
            ]
        self._fill(frame.detail_table, rows)

    def _render_chart(self, frame: ctk.CTkFrame, name: str) -> None:
        axis = frame.chart_axis
        axis.clear()
        dark = self.theme_mode == "Dark"
        text_color = "#dbeafe" if dark else "#17324d"
        muted_color = "#b9c8d6" if dark else "#526579"
        axis.set_facecolor("#172737" if dark else "#ffffff")
        axis.tick_params(colors=muted_color, labelsize=8)
        for spine in axis.spines.values():
            spine.set_color("#36536b" if dark else "#d5dee8")
        if name == "Traffic":
            traffic = self.snapshot["traffic"]
            labels = [row[0] for row in traffic]
            axis.plot(labels, [row[1] for row in traffic], label="In", color="#2563eb")
            axis.plot(labels, [row[2] for row in traffic], label="Out", color="#f97316")
            axis.set_ylabel("People per hour", color=muted_color)
            legend = axis.legend(facecolor="#1d3346" if dark else "#ffffff", edgecolor="#36536b" if dark else "#d5dee8")
            for label in legend.get_texts():
                label.set_color(text_color)
        else:
            rows = list(reversed(self.snapshot["occupancy" if name == "Occupancy" else "queue"]))
            values = [row.current_count if name == "Occupancy" else row.queue_length for row in rows]
            axis.plot([str(index + 1) for index in range(len(values))], values, marker="o", color="#2563eb")
            axis.set_ylabel("People" if name == "Occupancy" else "Queue length", color=muted_color)
            axis.set_xlabel("Oldest to newest reading", color=muted_color)
        axis.grid(axis="y", alpha=0.25)
        axis.set_title(
            "Hourly movement" if name == "Traffic" else f"{name} history",
            loc="left", color=text_color, fontweight="bold",
        )
        frame.chart.figure.tight_layout()
        frame.chart.draw_idle()

    def _close(self) -> None:
        self.stop_event.set()
        self.destroy()


def main() -> None:
    Dashboard().mainloop()


if __name__ == "__main__":
    main()