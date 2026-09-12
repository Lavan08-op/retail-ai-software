"""InferenceEngine contract. Real implementation (Qualcomm Detectron2) is
the teammate's — NOT built here. This Protocol is the whole handoff: as
long as their QualcommInferenceEngine.infer() returns list[Detection] in
this shape given a FrameData, nothing else in the system needs to change.

Takes FrameData (metadata + actual pixels), not just Frame — a real model
needs real pixel data to run inference on.
"""

from typing import Protocol

from core.frame_data import FrameData
from core.models import Detection


class InferenceEngine(Protocol):
    """Implementations: MockInferenceEngine (mine, now),
    QualcommInferenceEngine (teammate's, later)."""

    def infer(self, frame_data: FrameData) -> list[Detection]: ...
