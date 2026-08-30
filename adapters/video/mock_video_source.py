"""Mock VideoSource — generates fake frames without any real camera or
GStreamer. Lets everything downstream (inference, tracking, analytics) be
built and tested before the teammate's real GStreamer receiver exists."""

from core.models import Frame


class MockVideoSource:
    """Implements the VideoSource Protocol. Produces a new fake Frame each
    time get_frame() is called, incrementing frame_index. Always
    "connected" since there's no real hardware to fail here."""

    def __init__(self, camera_id: str, width: int = 1280, height: int = 720):
        self._camera_id = camera_id
        self._width = width
        self._height = height
        self._frame_index = 0

    def get_frame(self) -> Frame | None:
        self._frame_index += 1
        return Frame(
            camera_id=self._camera_id,
            width=self._width,
            height=self._height,
            frame_index=self._frame_index,
        )

    def is_connected(self) -> bool:
        return True

    def camera_id(self) -> str:
        return self._camera_id
