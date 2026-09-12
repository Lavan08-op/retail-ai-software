"""Threaded live camera pipeline using the existing analytics service."""

from __future__ import annotations

import threading

from adapters.inference.ultralytics_engine import UltralyticsInferenceEngine
from adapters.tracking.simple_tracker import SimpleTracker
from adapters.video.opencv_rtsp_source import OpenCVRTSPVideoSource
from config.loader import load_camera_zone_map
from pipeline.runner import PipelineRunner
from services.analytics_service import AnalyticsService
from storage import writer


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
        zone_map = load_camera_zone_map()
        self.runners = [
            PipelineRunner(
                video_source=OpenCVRTSPVideoSource(camera_id, url),
                inference_engine=UltralyticsInferenceEngine(model_path=model_path),
                tracker=SimpleTracker(),
                analytics_service=self.analytics_service,
                camera_zone_map=zone_map,
                detection_sink=lambda detections, camera_id=camera_id: self._persist_detections(camera_id, detections),
            )
            for camera_id, url in camera_urls.items()
        ]
        self.threads: list[threading.Thread] = []

        for camera_id in camera_urls:
            writer.upsert_camera(
                camera_id,
                label=camera_id,
                zone_id=zone_map.get(camera_id),
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
        while not self.stop_event.is_set():
            runner.run_once()
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> None:
        self.stop_event.set()
        for runner in self.runners:
            close = getattr(runner.video_source, "close", None)
            if close is not None:
                close()
        for thread in self.threads:
            thread.join(timeout=3)
        self.threads.clear()
