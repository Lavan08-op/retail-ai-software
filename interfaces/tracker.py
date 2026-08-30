"""Tracker contract. Real implementation is the teammate's — this file is
what they build against. analytics/ only ever depends on this Protocol."""

from typing import Protocol

from core.models import Detection, Track


class Tracker(Protocol):
    """Implementations: MockTracker (mine, now), RealTracker (teammate's,
    later). update() is called once per frame's worth of detections and
    returns the current set of tracked objects with persistent IDs."""

    def update(self, detections: list[Detection]) -> list[Track]: ...
