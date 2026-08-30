"""CameraService — thin orchestration over camera registration/status.
Callers (pipeline, PySide6, Streamlit, a future Flask API) use this, never
storage.writer or storage.repositories directly."""

from datetime import datetime, timezone

from storage import repositories, writer
from storage.models import Camera


class CameraService:
    def register_camera(self, camera_id: str, label: str, zone_id: str | None = None) -> None:
        writer.upsert_camera(camera_id, label, zone_id=zone_id, online=True, last_seen=datetime.now(timezone.utc))

    def mark_offline(self, camera_id: str, label: str, zone_id: str | None = None) -> None:
        writer.upsert_camera(camera_id, label, zone_id=zone_id, online=False, last_seen=datetime.now(timezone.utc))

    def list_cameras(self) -> list[Camera]:
        return repositories.list_cameras()
