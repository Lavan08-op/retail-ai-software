from __future__ import annotations

import numpy as np

from adapters.video.opencv_rtsp_source import OpenCVRTSPVideoSource


class _Capture:
    def __init__(self, image):
        self.image = image
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        return True, self.image

    def release(self):
        self.released = True


def test_rtsp_source_reads_frame_metadata_and_pixels():
    image = np.zeros((24, 32, 3), dtype=np.uint8)
    capture = _Capture(image)
    source = OpenCVRTSPVideoSource(
        "entry-cam",
        "rtsp://127.0.0.1:8554/entry-cam",
        capture_factory=lambda _: capture,
        reconnect_delay_seconds=0,
    )

    frame = source.get_frame()

    assert frame is not None
    assert frame.metadata.camera_id == "entry-cam"
    assert frame.metadata.width == 32
    assert frame.metadata.height == 24
    assert frame.metadata.frame_index == 1
    assert frame.image is image
    assert source.is_connected() is True


def test_rtsp_source_releases_failed_stream():
    class FailedCapture(_Capture):
        def isOpened(self):
            return False

    capture = FailedCapture(np.zeros((2, 2, 3), dtype=np.uint8))
    source = OpenCVRTSPVideoSource(
        "entry-cam",
        "rtsp://127.0.0.1:8554/entry-cam",
        capture_factory=lambda _: capture,
        reconnect_delay_seconds=0,
    )

    assert source.get_frame() is None
    assert source.is_connected() is False
    assert capture.released is True