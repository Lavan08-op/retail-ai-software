from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from integrations.edge_gateway import QueueGatewayPublisher, queue_payload


class _Handler(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        self.__class__.received.append(json.loads(self.rfile.read(length)))
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        return


def test_queue_payload_is_server_contract():
    payload = queue_payload(7)
    assert payload["queue_count"] == 7
    assert payload["camera_id"] == "queue-cam-1"
    assert "timestamp" in payload
    assert payload["stale"] is False


def test_queue_gateway_publishes_and_stops():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    publisher = QueueGatewayPublisher(
        f"http://127.0.0.1:{server.server_address[1]}/api/v1/queue",
        lambda: queue_payload(7),
        interval_seconds=0.01,
    )
    publisher.start()
    try:
        publisher.stop_event.wait(0.1)
        assert publisher.thread is not None
        assert publisher.thread.is_alive()
    finally:
        publisher.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
    assert _Handler.received
    assert _Handler.received[0]["queue_count"] == 7
