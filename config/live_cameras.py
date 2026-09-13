"""Environment-driven live camera configuration."""

from __future__ import annotations

from collections.abc import Mapping
import os


DEFAULT_CAMERA_IDS = ("entry-cam", "queue-cam-1", "queue-cam-2", "shelf-cam-1")


def _environment_key(camera_id: str) -> str:
    return camera_id.upper().replace("-", "_")


def _split_camera_ids(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def load_live_camera_urls(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return camera IDs and stream URLs without machine-specific hardcoding."""

    source = env if env is not None else os.environ
    camera_ids = _split_camera_ids(source.get("STORESENSE_CAMERA_IDS", "")) or DEFAULT_CAMERA_IDS
    base_url = source.get("STORESENSE_RTSP_BASE_URL", "rtsp://127.0.0.1:8554")
    return {
        camera_id: source.get(
            f"STORESENSE_RTSP_URL_{_environment_key(camera_id)}",
            f"{base_url.rstrip('/')}/{camera_id}",
        )
        for camera_id in camera_ids
    }
