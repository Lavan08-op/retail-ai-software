"""Optional server-to-edge queue publisher.

The server remains the source of truth. A Raspberry Pi can expose a small
HTTP endpoint and receive the latest queue payload without running AI.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Callable


class QueueGatewayPublisher:
    def __init__(
        self,
        endpoint: str,
        queue_reader: Callable[[], dict],
        interval_seconds: float = 1.0,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.queue_reader = queue_reader
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, name="edge-queue-publisher", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                payload = self.queue_reader()
                body = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    self.endpoint,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    if response.status >= 300:
                        raise RuntimeError(f"gateway returned HTTP {response.status}")
                self.last_error = None
            except (OSError, urllib.error.URLError, RuntimeError) as error:
                self.last_error = str(error)
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=3)


def queue_payload(
    queue_length: int,
    camera_id: str = "queue-cam-1",
    zone_id: str = "checkout-1",
    stale: bool = False,
) -> dict:
    return {
        "queue_count": int(queue_length),
        "camera_id": camera_id,
        "zone_id": zone_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stale": stale,
    }
