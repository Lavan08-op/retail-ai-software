"""Small HTTP API backed by the existing read-only repositories."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from storage import repositories


def _timestamp(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _metrics() -> dict[str, Any]:
    return {
        "entry_exit": repositories.entry_exit_counts(),
        "queue": [
            {
                "camera_id": item.camera_id,
                "zone_id": item.zone_id,
                "queue_length": item.queue_length,
                "avg_wait_seconds": item.avg_wait_seconds,
                "timestamp": _timestamp(item.timestamp),
            }
            for item in repositories.recent_queue_metrics(limit=50)
        ],
        "inventory": [
            {
                "camera_id": item.camera_id,
                "products": item.products_json,
                "timestamp": _timestamp(item.timestamp),
            }
            for item in repositories.recent_inventory_snapshots(limit=50)
        ],
        "detections": [
            {
                "camera_id": item.camera_id,
                "class_name": item.class_name,
                "confidence": item.confidence,
                "bbox": item.bbox_json,
                "timestamp": _timestamp(item.timestamp),
            }
            for item in repositories.recent_detections(limit=100)
        ],
        "alerts": [
            {
                "alert_id": item.alert_id,
                "severity": item.severity,
                "message": item.message,
                "status": item.status,
                "created_at": _timestamp(item.created_at),
            }
            for item in repositories.active_alerts()
        ],
    }


class _RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._send({"status": "ok"})
        elif self.path in {"/api/metrics", "/api/v1/metrics"}:
            self._send(_metrics())
        else:
            self.send_response(404)
            self.end_headers()

    def _send(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class StoreSenseAPIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.server = ThreadingHTTPServer((host, port), _RequestHandler)
        self.thread: Thread | None = None

    def start(self) -> None:
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)


if __name__ == "__main__":
    api = StoreSenseAPIServer()
    api.start()
    print("StoreSense API listening on http://127.0.0.1:8080")
    try:
        api.thread.join()
    except KeyboardInterrupt:
        api.stop()
