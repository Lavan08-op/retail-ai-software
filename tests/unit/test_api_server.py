from __future__ import annotations

import json
from urllib.request import urlopen

from api.server import StoreSenseAPIServer


def test_api_exposes_health_and_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAIL_AI_DB_PATH", str(tmp_path / "api.db"))
    from storage.database import init_db

    init_db()
    api = StoreSenseAPIServer("127.0.0.1", 0)
    api.start()
    try:
        port = api.server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/health") as response:
            assert json.load(response)["status"] == "ok"
        with urlopen(f"http://127.0.0.1:{port}/api/metrics") as response:
            payload = json.load(response)
            assert set(payload["entry_exit"]) == {"in", "out"}
            assert isinstance(payload["queue"], list)
        with urlopen(f"http://127.0.0.1:{port}/api/v1/queue/latest") as response:
            assert "queue_count" in json.load(response)
        with urlopen(f"http://127.0.0.1:{port}/api/v1/status") as response:
            status = json.load(response)
            assert status["server"]["healthy"] is True
    finally:
        api.stop()
