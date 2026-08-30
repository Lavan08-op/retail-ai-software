"""People counting analytics — pure Python business logic. Consumes Track
objects (from a real or mock Tracker) and produces AnalyticsResult
objects. Must never import PySide6, Streamlit, Flask, RabbitMQ, or any
storage/database module directly — callers decide what to do with the
result (e.g. storage/writer.py persists it, or a test just asserts on
it)."""

from collections import defaultdict

from core.models import AnalyticsResult, Track


class PeopleCounter:
    """Tracks the current visible-people count, overall and per camera.
    Call update() once per frame's worth of tracks; it returns a list of
    AnalyticsResult objects ready to hand to storage or an event engine."""

    def __init__(self):
        self._history: list[AnalyticsResult] = []

    def update(self, tracks: list[Track]) -> list[AnalyticsResult]:
        people = [t for t in tracks if t.class_name == "person"]

        per_camera: dict[str, int] = defaultdict(int)
        for t in people:
            per_camera[t.camera_id] += 1

        results = [
            AnalyticsResult(
                metric_name="people_count_total",
                value=float(len(people)),
                unit="people",
            )
        ]
        for camera_id, count in per_camera.items():
            results.append(
                AnalyticsResult(
                    metric_name="people_count_camera",
                    camera_id=camera_id,
                    value=float(count),
                    unit="people",
                )
            )

        self._history.extend(results)
        return results

    def history(self) -> list[AnalyticsResult]:
        return list(self._history)
