"""The real-time pipeline loop: video -> inference -> tracker -> [zone
assignment] -> services.

Runs entirely on mock adapters right now. When the teammate's
GStreamerVideoSource and QualcommInferenceEngine are ready, only the two
lines that CONSTRUCT a PipelineRunner change (wherever it's wired up) —
this file's run_once/run_forever logic never changes, since it only ever
talks to the VideoSource/InferenceEngine/Tracker Protocols, never a
concrete class.

camera_zone_map is optional and defaults to no mapping at all (tracks
pass through unchanged) — existing callers that don't pass one keep
today's exact behavior. Pass config.loader.load_camera_zone_map() to
actually populate Track.zone_id from config/settings.yaml and light up
the zone-based analytics modules (occupancy, queue_monitor, shelf_monitor).
"""

import time
from collections.abc import Callable

from interfaces.inference_engine import InferenceEngine
from interfaces.tracker import Tracker
from interfaces.video_source import VideoSource
from pipeline.zone_mapper import assign_zones
from services.analytics_service import AnalyticsService
from core.models import Detection


class PipelineRunner:
    def __init__(
        self,
        video_source: VideoSource,
        inference_engine: InferenceEngine,
        tracker: Tracker,
        analytics_service: AnalyticsService,
        camera_zone_map: dict[str, str] | None = None,
        detection_sink: Callable[[list[Detection]], None] | None = None,
    ):
        self.video_source = video_source
        self.inference_engine = inference_engine
        self.tracker = tracker
        self.analytics_service = analytics_service
        self.camera_zone_map = camera_zone_map or {}
        self.detection_sink = detection_sink

    def run_once(self) -> None:
        frame_data = self.video_source.get_frame()
        if frame_data is None:
            return
        detections = self.inference_engine.infer(frame_data)
        if self.detection_sink is not None:
            self.detection_sink(detections)
        tracks = self.tracker.update(detections)
        if self.camera_zone_map:
            tracks = assign_zones(tracks, self.camera_zone_map)
        self.analytics_service.process_tracks(tracks)

    def run_n(self, n: int) -> None:
        """Run a fixed number of iterations — what tests use, and a good
        way to sanity-check the pipeline manually before trusting
        run_forever()."""
        for _ in range(n):
            self.run_once()

    def run_forever(self, interval_seconds: float = 1.0) -> None:
        while True:
            self.run_once()
            time.sleep(interval_seconds)
