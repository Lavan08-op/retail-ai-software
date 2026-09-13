"""Threaded live camera pipeline using the existing analytics service."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from adapters.inference.ultralytics_engine import UltralyticsInferenceEngine
from adapters.tracking.simple_tracker import SimpleTracker
from adapters.video.opencv_rtsp_source import OpenCVRTSPVideoSource
from config.loader import load_camera_zone_map
from pipeline.runner import PipelineRunner
from services.analytics_service import AnalyticsService
from storage import writer

# How often (seconds) an unchanged online/offline state is re-written to the
# DB. State *changes* (connected -> disconnected or back) are always written
# immediately regardless of this interval.
STATUS_WRITE_INTERVAL_SECONDS = 2.0


class LivePipeline:
    def __init__(
        self,
        camera_urls: dict[str, str],
        model_path: str = "yolo11n.pt",
        analytics_service: AnalyticsService | None = None,
        interval_seconds: float = 0.05,
    ) -> None:
        self.stop_event = threading.Event()
        self.interval_seconds = interval_seconds
        self.analytics_service = analytics_service or AnalyticsService()
        self.zone_map = load_camera_zone_map()
        self.runners = [
            PipelineRunner(
                video_source=OpenCVRTSPVideoSource(camera_id, url),
                inference_engine=UltralyticsInferenceEngine(model_path=model_path),
                tracker=SimpleTracker(),
                analytics_service=self.analytics_service,
                camera_zone_map=self.zone_map,
                detection_sink=lambda detections, camera_id=camera_id: self._persist_detections(camera_id, detections),
            )
            for camera_id, url in camera_urls.items()
        ]
        self.threads: list[threading.Thread] = []

        # Real connection-state tracking (fixes cameras being stuck at the
        # startup "online=False" row forever - see _update_camera_status).
        self._last_online: dict[str, bool | None] = {}
        self._last_seen: dict[str, datetime | None] = {}
        self._last_status_write: dict[str, float] = {}

        for camera_id in camera_urls:
            self._last_online[camera_id] = None
            self._last_seen[camera_id] = None
            writer.upsert_camera(
                camera_id,
                label=camera_id,
                zone_id=self.zone_map.get(camera_id),
                online=False,
                last_seen=None,
            )

    @staticmethod
    def _persist_detections(camera_id, detections) -> None:
        for detection in detections:
            writer.write_detection(
                camera_id,
                detection.class_id,
                detection.class_name,
                detection.confidence,
                detection.bbox,
            )

    def start(self) -> None:
        for runner in self.runners:
            thread = threading.Thread(target=self._run_runner, args=(runner,), daemon=True)
            thread.start()
            self.threads.append(thread)

    def _run_runner(self, runner: PipelineRunner) -> None:
        camera_id = runner.video_source.camera_id()
        while not self.stop_event.is_set():
            runner.run_once()
            self._update_camera_status(camera_id, runner.video_source)
            self.stop_event.wait(self.interval_seconds)

    def _update_camera_status(self, camera_id: str, video_source) -> None:
        """Write the camera's REAL connection state to storage, throttled.

        The startup row defaults to offline, but the live pipeline must flip it to
        online as soon as the RTSP source actually reads a frame and stays in sync
        with subsequent reconnects.
        """
        is_connected = bool(getattr(video_source, "is_connected", lambda: False)())
        now = time.monotonic()

        if is_connected:
            self._last_seen[camera_id] = datetime.now(timezone.utc)

        state_changed = self._last_online.get(camera_id) != is_connected
        last_written = self._last_status_write.get(camera_id, 0.0)
        if not state_changed and (now - last_written) < STATUS_WRITE_INTERVAL_SECONDS:
            return

        self._last_online[camera_id] = is_connected
        self._last_status_write[camera_id] = now
        writer.upsert_camera(
            camera_id,
            label=camera_id,
            zone_id=self.zone_map.get(camera_id),
            online=is_connected,
            last_seen=self._last_seen.get(camera_id),
        )

    def stop(self) -> None:
        self.stop_event.set()
        for runner in self.runners:
            close = getattr(runner.video_source, "close", None)
            if close is not None:
                close()
        for thread in self.threads:
            thread.join(timeout=3)
        self.threads.clear()
