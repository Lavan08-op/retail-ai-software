from __future__ import annotations

import pytest

from app.start_storesense import StoreSenseLauncher

_REAL_IMPORT = __import__


def test_dashboard_dependency_failure_prevents_system_ready(tmp_path, monkeypatch):
    launcher = StoreSenseLauncher(
        runtime_dir=tmp_path / "runtime",
        start_hardware=False,
        start_dashboard=True,
        start_api=False,
    )

    monkeypatch.setattr("builtins.__import__", _missing_customtkinter_import)
    with pytest.raises(RuntimeError, match="Dashboard failed to start"):
        launcher.start()
    assert launcher.dashboard_error is not None


def _missing_customtkinter_import(name, *args, **kwargs):
    if name == "customtkinter":
        raise ImportError("customtkinter unavailable for lifecycle test")
    return _REAL_IMPORT(name, *args, **kwargs)
