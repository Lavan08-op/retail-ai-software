"""Focused tests for the unified StoreSense lifecycle."""

from __future__ import annotations

import time

from start_storesense import StoreSenseLauncher


def test_launcher_starts_bridge_in_a_temporary_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAIL_AI_DB_PATH", str(tmp_path / "storesense.db"))
    launcher = StoreSenseLauncher(
        runtime_dir=tmp_path / "runtime-dev",
        start_hardware=False,
        start_dashboard=False,
        bridge_interval=0.01,
    )

    launcher.start()
    try:
        assert launcher.runtime_dir == tmp_path / "runtime-dev"
        assert launcher.bridge_thread is not None
        assert launcher.bridge_thread.is_alive()
        assert not launcher.processes
    finally:
        launcher.shutdown()

    deadline = time.monotonic() + 1
    while launcher.bridge_thread is not None and launcher.bridge_thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert launcher.bridge_thread is not None
    assert not launcher.bridge_thread.is_alive()


def test_launcher_does_not_start_missing_hardware_root(tmp_path):
    launcher = StoreSenseLauncher(
        runtime_dir=tmp_path / "runtime-dev",
        hardware_root=tmp_path / "missing-hardware",
        start_hardware=True,
        start_dashboard=False,
    )

    launcher.start()
    try:
        assert launcher.processes == []
    finally:
        launcher.shutdown()
