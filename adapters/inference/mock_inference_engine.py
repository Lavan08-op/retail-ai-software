"""Mock InferenceEngine — returns fake detections without any real AI
model. The teammate's QualcommInferenceEngine implements this same
Protocol later; nothing downstream needs to change when that swap
happens.

Genuinely reads frame_data.image (not just frame_data.metadata) — computes
mean pixel brightness and includes it in each Detection's metadata. This
isn't needed for the fake detections themselves, but it proves the actual
pixel array flows all the way from VideoSource through to here, rather
than the pipeline silently ignoring it — the whole point of the FrameData
change.
"""

import random

from core.frame_data import FrameData
from core.models import Detection


class MockInferenceEngine:
    """Implements the InferenceEngine Protocol. Returns a small, randomized
    set of fake "person" detections per frame — enough for analytics
    modules to have something realistic to consume."""

    def __init__(self, min_people: int = 0, max_people: int = 4, seed: int | None = None):
        self._min_people = min_people
        self._max_people = max_people
        self._rng = random.Random(seed)

    def infer(self, frame_data: FrameData) -> list[Detection]:
        frame = frame_data.metadata
        image = frame_data.image

        # Genuinely reads the pixel array — proves it actually arrived,
        # not just that a placeholder object was passed around.
        mean_brightness = float(image.mean())

        count = self._rng.randint(self._min_people, self._max_people)
        detections = []
        for _ in range(count):
            x1 = self._rng.uniform(0, max(frame.width - 100, 1))
            y1 = self._rng.uniform(0, max(frame.height - 200, 1))
            detections.append(
                Detection(
                    camera_id=frame.camera_id,
                    class_id=0,
                    class_name="person",
                    confidence=self._rng.uniform(0.7, 0.99),
                    bbox=(x1, y1, x1 + 80, y1 + 180),
                    metadata={"frame_mean_brightness": round(mean_brightness, 2)},
                )
            )
        return detections
