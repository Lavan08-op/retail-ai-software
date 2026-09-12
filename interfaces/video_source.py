"""VideoSource contract. Real implementation (GStreamer receiver) is the
teammate's — this file is what they build against. My code only ever
depends on this Protocol, never on a concrete class.

Returns FrameData (metadata + actual pixel array), not just Frame — a
real inference engine needs real pixels, not only camera_id/timestamp/
width/height. See core/frame_data.py for why these are kept separate.
"""

from typing import Protocol

from core.frame_data import FrameData


class VideoSource(Protocol):
    """Something that can produce frames for a given camera_id.
    Implementations: MockVideoSource, FileVideoSource (mine, now),
    GStreamerVideoSource (teammate's, later)."""

    def get_frame(self) -> FrameData | None:
        """Return the latest available frame (metadata + pixels), or None
        if none is ready. Implementations should prefer the LATEST frame
        and drop backlog rather than queuing every frame — matches the
        low-latency requirement in the streaming architecture."""
        ...

    def is_connected(self) -> bool: ...

    def camera_id(self) -> str: ...
