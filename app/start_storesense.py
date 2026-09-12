"""Unified StoreSense lifecycle for the existing hardware and software repos."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


class StoreSenseLauncher:
    def __init__(
        self,
        runtime_dir: str | Path | None = None,
        hardware_root: str | Path | None = None,
        start_hardware: bool = True,
        start_dashboard: bool = True,
        start_api: bool = True,
        start_live_ai: bool = False,
        development_mode: bool = False,
        bridge_interval: float = 2.0,
    ) -> None:
        self.runtime_dir = Path(
            runtime_dir
            or os.environ.get("RETAIL_EDGE_RUNTIME_DIR", PROJECT_ROOT / ".runtime-dev")
        )
        self.hardware_root = Path(
            hardware_root or os.environ.get("STORESENSE_HARDWARE_ROOT", "")
        ) if (hardware_root or os.environ.get("STORESENSE_HARDWARE_ROOT")) else None
        self.start_hardware = start_hardware
        self.start_dashboard = start_dashboard
        self.start_api = start_api
        self.start_live_ai = start_live_ai
        self.development_mode = development_mode
        self.bridge_interval = bridge_interval
        self.processes: list[subprocess.Popen] = []
        self.bridge_stop = threading.Event()
        self.bridge_thread: threading.Thread | None = None
        self.api_server = None
        self.live_pipeline = None
        self.dashboard_process = None
        self.dashboard_error = None
        self.dev_stop = threading.Event()
        self.dev_thread: threading.Thread | None = None
        self.edge_gateway = None

    def start(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        os.environ["RETAIL_EDGE_RUNTIME_DIR"] = str(self.runtime_dir)
        print(f"[STORESENSE] Starting with runtime directory: {self.runtime_dir}")

        from storage.database import init_db

        init_db()
        print("[DATABASE] Ready")

        if self.start_hardware:
            self._start_hardware()
        elif self.development_mode:
            self._start_development_hardware()
        else:
            print("[HARDWARE] Disabled")

        from integrations.hardware_bridge import HardwareMetricsBridge

        bridge = HardwareMetricsBridge(self.runtime_dir)
        self.bridge_thread = threading.Thread(target=self._run_bridge, args=(bridge,), daemon=True)
        self.bridge_thread.start()
        print("[BRIDGE] Started")
        print("[ANALYTICS] Existing analytics and storage services ready")

        if self.start_live_ai:
            self._start_live_ai()
        else:
            print("[AI] Live RTSP/YOLO pipeline disabled")

        if self.start_api:
            try:
                self._start_api()
            except RuntimeError as error:
                print(f"[API] FAILED: {error}")
                print("[STORESENSE] NOT READY")
                self.shutdown()
                raise
        else:
            print("[API] Disabled")

        self._start_edge_gateway()

        if self.start_dashboard:
            self._start_dashboard()
        else:
            print("[DASHBOARD] Disabled")
        if self.dashboard_error is not None:
            print(f"[DASHBOARD] FAILED: {self.dashboard_error}")
            print("[STORESENSE] NOT READY")
            self.shutdown()
            raise RuntimeError(f"Dashboard failed to start: {self.dashboard_error}")
        print("[STORESENSE] SYSTEM READY")

    def _start_live_ai(self) -> None:
        from config.live_cameras import load_live_camera_urls
        from services.live_pipeline import LivePipeline

        model_path = os.environ.get("STORESENSE_MODEL_PATH", "yolo11n.pt")
        self.live_pipeline = LivePipeline(load_live_camera_urls(), model_path=model_path)
        self.live_pipeline.start()
        print("[AI] Live RTSP/YOLO pipeline started")

    def _start_development_hardware(self) -> None:
        from simulation.runtime_hardware import RuntimeHardwareSimulator

        simulator = RuntimeHardwareSimulator(self.runtime_dir)
        self.dev_thread = threading.Thread(target=simulator.run, args=(self.dev_stop,), daemon=True)
        self.dev_thread.start()
        print("[HARDWARE] Development runtime simulator started")

    def _start_api(self) -> None:
        from api.server import StoreSenseAPIServer

        host = os.environ.get("STORESENSE_API_HOST", "127.0.0.1")
        port = int(os.environ.get("STORESENSE_API_PORT", "8080"))
        try:
            self.api_server = StoreSenseAPIServer(host, port)
            self.api_server.start()
        except OSError as error:
            self.api_server = None
            raise RuntimeError(f"API failed to bind {host}:{port}: {error}") from error
        print(f"[API] Started at http://{host}:{port}")

    def _start_edge_gateway(self) -> None:
        endpoint = os.environ.get("STORESENSE_EDGE_GATEWAY_URL", "").strip()
        if not endpoint:
            print("[EDGE] Gateway output disabled (set STORESENSE_EDGE_GATEWAY_URL to enable)")
            return
        from integrations.edge_gateway import QueueGatewayPublisher, queue_payload
        from storage import repositories

        def latest_queue() -> dict:
            metric = repositories.latest_queue_metric()
            stale = True
            if metric is not None:
                timestamp = metric.timestamp
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                stale = (datetime.now(timezone.utc) - timestamp).total_seconds() > 30
            return queue_payload(
                metric.queue_length if metric and not stale else 0,
                metric.camera_id if metric else "queue-cam-1",
                metric.zone_id if metric and metric.zone_id else "checkout-1",
                stale=stale,
            )

        self.edge_gateway = QueueGatewayPublisher(
            endpoint,
            latest_queue,
            interval_seconds=float(os.environ.get("STORESENSE_EDGE_GATEWAY_INTERVAL", "1")),
        )
        self.edge_gateway.start()
        print(f"[EDGE] Queue publisher started: {endpoint}")

    def _start_hardware(self) -> None:
        if self.hardware_root is None:
            print("[HARDWARE] Not started: set STORESENSE_HARDWARE_ROOT or --hardware-root")
            return
        launcher = self.hardware_root / "deploy" / "launch_retailedge.py"
        if not launcher.exists():
            print(f"[HARDWARE] Not started: launcher not found at {launcher}")
            return
        env = os.environ.copy()
        env["RETAIL_EDGE_RUNTIME_DIR"] = str(self.runtime_dir)
        process = subprocess.Popen(
            [sys.executable, str(launcher), "--no-dashboard"],
            cwd=str(self.hardware_root),
            env=env,
        )
        self.processes.append(process)
        print(f"[HARDWARE] Started existing launcher (pid {process.pid})")

    def _start_dashboard(self) -> None:
        env = os.environ.copy()
        env["RETAIL_EDGE_RUNTIME_DIR"] = str(self.runtime_dir)
        try:
            import customtkinter  # noqa: F401
        except ImportError as error:
            self.dashboard_error = error
            return
        process = subprocess.Popen(
            [sys.executable, "-m", "dashboard.app"],
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.75)
        if process.poll() is not None:
            _, stderr = process.communicate()
            self.dashboard_error = stderr.strip() or f"exited with code {process.returncode}"
            return
        self.dashboard_process = process
        self.processes.append(process)
        print(f"[DASHBOARD] READY (pid {process.pid})")

    def _run_bridge(self, bridge) -> None:
        while not self.bridge_stop.is_set():
            try:
                print(f"[BRIDGE] {bridge.poll_once()}")
            except Exception as error:
                print(f"[BRIDGE] Poll failed: {error}")
            self.bridge_stop.wait(self.bridge_interval)

    def run_forever(self) -> None:
        try:
            while True:
                active = [process for process in self.processes if process.poll() is None]
                if self.processes and not active:
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("[STORESENSE] Shutdown requested")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.bridge_stop.set()
        self.dev_stop.set()
        if self.live_pipeline is not None:
            self.live_pipeline.stop()
        if self.api_server is not None:
            self.api_server.stop()
        if self.edge_gateway is not None:
            self.edge_gateway.stop()
        if self.bridge_thread is not None:
            self.bridge_thread.join(timeout=3)
        if self.dev_thread is not None:
            self.dev_thread.join(timeout=3)
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
        for process in self.processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self.processes.clear()
        print("[STORESENSE] Shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the existing StoreSense hardware/software components.")
    parser.add_argument("--runtime-dir", help="Shared runtime directory; defaults to RETAIL_EDGE_RUNTIME_DIR or .runtime-dev")
    parser.add_argument("--hardware-root", help="Hardware repository root; defaults to STORESENSE_HARDWARE_ROOT")
    parser.add_argument("--no-hardware", action="store_true", help="Do not start the hardware repository launcher")
    parser.add_argument("--no-dashboard", action="store_true", help="Do not start the software dashboard")
    parser.add_argument("--no-api", action="store_true", help="Do not start the StoreSense API")
    parser.add_argument("--live-ai", action="store_true", help="Start OpenCV RTSP plus YOLO processing")
    parser.add_argument("--dev-mode", action="store_true", help="Generate runtime JSON through the bridge for local development")
    parser.add_argument("--bridge-interval", type=float, default=2.0)
    args = parser.parse_args()

    launcher = StoreSenseLauncher(
        runtime_dir=args.runtime_dir,
        hardware_root=args.hardware_root,
        start_hardware=not args.no_hardware,
        start_dashboard=not args.no_dashboard,
        start_api=not args.no_api,
        start_live_ai=args.live_ai,
        development_mode=args.dev_mode,
        bridge_interval=args.bridge_interval,
    )
    launcher.start()
    launcher.run_forever()


if __name__ == "__main__":
    main()
