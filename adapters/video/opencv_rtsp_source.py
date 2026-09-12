"""OpenCV RTSP video source for the live StoreSense pipeline."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from core.frame_data import FrameData
from core.models import Frame


class OpenCVRTSPVideoSource:
    """Read the newest frame from an RTSP stream with reconnect handling."""

    def __init__(
        self,
        camera_id: str,
        rtsp_url: str,
        capture_factory: Callable[[str], Any] | None = None,
        reconnect_delay_seconds: float = 2.0,
    ) -> None:
        self._camera_id = camera_id
        self._rtsp_url = rtsp_url
        self._capture_factory = capture_factory
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self._capture: Any | None = None
        self._frame_index = 0
        self._last_attempt = 0.0
        self._connected = False

    def _factory(self) -> Callable[[str], Any]:
        if self._capture_factory is not None:
            return self._capture_factory
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError("OpenCV is required for RTSP video sources; install the live dependencies") from error
        return cv2.VideoCapture

    def _connect(self) -> None:
        now = time.monotonic()
        if now - self._last_attempt < self._reconnect_delay_seconds:
            return
        self._last_attempt = now
        capture = self._factory()(self._rtsp_url)
        if hasattr(capture, "set"):
            try:
                import cv2
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except (ImportError, AttributeError):
                pass
        if capture.isOpened():
            self._capture = capture
            self._connected = True
        else:
            capture.release()
            self._connected = False

    def get_frame(self) -> FrameData | None:
        if self._capture is None or not self._connected:
            self._connect()
        if self._capture is None:
            return None
        ok, image = self._capture.read()
        if not ok or image is None:
            self._connected = False
            self._capture.release()
            self._capture = None
            return None
        self._frame_index += 1
        height, width = image.shape[:2]
        return FrameData(
            metadata=Frame(
                camera_id=self._camera_id,
                timestamp=datetime.now(timezone.utc),
                width=width,
                height=height,
                frame_index=self._frame_index,
            ),
            image=image,
        )

    def is_connected(self) -> bool:
        return self._connected

    def camera_id(self) -> str:
        return self._camera_id

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self._connected = False
