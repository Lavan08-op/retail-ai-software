"""FrameData — pairs the lightweight `Frame` metadata contract (Pydantic,
serializable, safe to log/store/pass through events) with the actual pixel
buffer a real inference engine needs to run on.

Why this isn't just added as a field on Frame itself: Frame is used
everywhere as a lightweight, serializable data contract — logging, events,
potentially over a future message bus. A raw pixel array (megabytes per
frame, at 720p) doesn't belong in that model. FrameData is the deliberately
NOT-Pydantic carrier used only where actual pixels need to travel alongside
metadata: VideoSource -> InferenceEngine, and nowhere else.

image is a numpy array, shape (height, width, 3), dtype uint8 — this is
the same shape OpenCV/most CV libraries use by convention (BGR or RGB
depending on source), so a real GStreamer/OpenCV VideoSource can hand this
straight through without reshaping anything.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.models import Frame


@dataclass
class FrameData:
    metadata: Frame
    image: np.ndarray
