"""Environment-driven live camera configuration."""

from __future__ import annotations

import os


DEFAULT_CAMERA_IDS = ("entry-cam", "queue-cam-1", "queue-cam-2", "shelf-cam-1", "shelf-cam-2")


def _environment_key(camera_id: str) -> str:
    return camera_id.upper().replace("-", "_")


def load_live_camera_urls() -> dict[str, str]:
    """Return camera IDs and RTSP URLs without machine-specific hardcoding."""

    configured_ids = os.environ.get("STORESENSE_CAMERA_IDS", "")
    camera_ids = tuple(item.strip() for item in configured_ids.split(",") if item.strip()) or DEFAULT_CAMERA_IDS
    base_url = os.environ.get("STORESENSE_RTSP_BASE_URL", "rtsp://127.0.0.1:8554")
    return {
        camera_id: os.environ.get(
            f"STORESENSE_RTSP_URL_{_environment_key(camera_id)}",
            f"{base_url.rstrip('/')}/{camera_id}",
        )
        for camera_id in camera_ids
    }
