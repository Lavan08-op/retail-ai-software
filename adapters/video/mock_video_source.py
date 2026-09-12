"""Mock VideoSource — generates fake frames AND fake pixel data, without
any real camera or GStreamer. Lets everything downstream (inference,
tracking, analytics) be built and tested — including the pixel-data path
a real inference engine actually needs — before the teammate's real
GStreamer receiver exists.
"""

import numpy as np

from core.frame_data import FrameData
from core.models import Frame


class MockVideoSource:
    """Implements the VideoSource Protocol. Produces a new fake FrameData
    each time get_frame() is called: real Frame metadata (incrementing
    frame_index) paired with a genuine numpy pixel array of the right
    shape — random noise, not a real image, but real enough that a
    downstream inference engine can actually run against it rather than
    receiving a placeholder.
    """

    def __init__(self, camera_id: str, width: int = 1280, height: int = 720, seed: int | None = None):
        self._camera_id = camera_id
        self._width = width
        self._height = height
        self._frame_index = 0
        self._rng = np.random.default_rng(seed)

    def get_frame(self) -> FrameData | None:
        self._frame_index += 1
        metadata = Frame(
            camera_id=self._camera_id,
            width=self._width,
            height=self._height,
            frame_index=self._frame_index,
        )
        # Shape (height, width, 3), dtype uint8 — the same convention
        # OpenCV/most CV pipelines use, so a real VideoSource can hand
        # this straight through without any reshaping downstream.
        image = self._rng.integers(0, 256, size=(self._height, self._width, 3), dtype=np.uint8)
        return FrameData(metadata=metadata, image=image)

    def is_connected(self) -> bool:
        return True

    def camera_id(self) -> str:
        return self._camera_id
