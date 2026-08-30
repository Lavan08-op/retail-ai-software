"""Loads config/settings.yaml. This is the one place that reads the YAML
file — everything else (pipeline, services) takes plain Python dicts/args,
so nothing downstream needs to know config comes from YAML at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "settings.yaml"


def load_settings(path: Path | str | None = None) -> dict[str, Any]:
    settings_path = Path(path) if path is not None else _DEFAULT_SETTINGS_PATH
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_camera_zone_map(path: Path | str | None = None) -> dict[str, str]:
    """Returns {camera_id: zone_id} from the `cameras:` list in
    settings.yaml. This is what lets Track objects get a real zone_id
    assigned (see pipeline/zone_mapper.py) instead of staying None."""
    settings = load_settings(path)
    return {
        cam["id"]: cam["zone_id"]
        for cam in settings.get("cameras", [])
        if "id" in cam and "zone_id" in cam
    }


def load_alert_thresholds(path: Path | str | None = None) -> dict[str, Any]:
    settings = load_settings(path)
    return settings.get("alert_thresholds", {})


def load_alert_cooldowns(path: Path | str | None = None) -> dict[str, int]:
    """Return per-event alert cooldowns from ``settings.yaml``."""
    settings = load_settings(path)
    return settings.get("alert_cooldown_seconds", {})
