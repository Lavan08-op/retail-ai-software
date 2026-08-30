"""VideoSource contract. Real implementation (GStreamer receiver) is the
teammate's — this file is what they build against. My code only ever
depends on this Protocol, never on a concrete class."""

from typing import Protocol

from core.models import Frame


class VideoSource(Protocol):
    """Something that can produce frames for a given camera_id.
    Implementations: MockVideoSource, FileVideoSource (mine, now),
    GStreamerVideoSource (teammate's, later)."""

    def get_frame(self) -> Frame | None:
        """Return the latest available frame, or None if none is ready.
        Implementations should prefer the LATEST frame and drop backlog
        rather than queuing every frame — matches the low-latency
        requirement in the streaming architecture."""
        ...

    def is_connected(self) -> bool: ...

    def camera_id(self) -> str: ...
