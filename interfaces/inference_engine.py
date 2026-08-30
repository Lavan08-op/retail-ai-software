"""InferenceEngine contract. Real implementation (Qualcomm Detectron2) is
the teammate's — NOT built here. This Protocol is the whole handoff: as
long as their QualcommInferenceEngine.infer() returns list[Detection] in
this shape, nothing else in the system needs to change."""

from typing import Protocol

from core.models import Detection, Frame


class InferenceEngine(Protocol):
    """Implementations: MockInferenceEngine (mine, now),
    QualcommInferenceEngine (teammate's, later)."""

    def infer(self, frame: Frame) -> list[Detection]: ...
