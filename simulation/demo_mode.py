"""Continuous demo data generator — what you'd actually leave running
during a live SIH demo, so the dashboard and control room show constantly
changing, semi-realistic data instead of a single static seed.

Usage:
    python -m simulation.demo_mode                       # runs until Ctrl+C
    python -m simulation.demo_mode --duration-seconds 60  # runs for 60s then stops
    python -m simulation.demo_mode --seed 42              # reproducible run
"""

from __future__ import annotations

import argparse
import random
import time

from adapters.inference.mock_inference_engine import MockInferenceEngine
from adapters.tracking.mock_tracker import MockTracker
from adapters.video.mock_video_source import MockVideoSource
from config.loader import load_camera_zone_map
from pipeline.runner import PipelineRunner
from services.analytics_service import AnalyticsService
from storage.database import init_db

CAMERA_IDS = [
    "shelf-cam-1",
    "shelf-cam-2",
    "shelf-cam-3",
    "entry-cam",
    "queue-cam-1",
    "queue-cam-2",
]

QUEUE_CAMERAS = [
    ("queue-cam-1", "checkout-1"),
    ("queue-cam-2", "checkout-2"),
]


def run_demo(
    duration_seconds: float | None = None,
    tick_seconds: float = 2.0,
    seed: int | None = None,
) -> int:
    """Runs the demo loop. Returns the number of ticks completed — mainly
    useful for tests, which run this for a short fixed duration and assert
    on the return value plus what landed in storage."""

    init_db()
    rng = random.Random(seed)
    zone_map = load_camera_zone_map()
    analytics_service = AnalyticsService()

    runners = {
        camera_id: PipelineRunner(
            video_source=MockVideoSource(camera_id),
            inference_engine=MockInferenceEngine(min_people=0, max_people=4, seed=rng.randint(0, 10_000)),
            tracker=MockTracker(),
            analytics_service=analytics_service,
            camera_zone_map=zone_map,
        )
        for camera_id in CAMERA_IDS
    }

    start = time.monotonic()
    tick = 0
    print("Demo running. Press Ctrl+C to stop.")
    try:
        while duration_seconds is None or (time.monotonic() - start) < duration_seconds:
            tick += 1
            for runner in runners.values():
                runner.run_once()

            # Occasionally simulate a queue spike so alerts genuinely fire
            # during the demo, not just quiet baseline numbers.
            for queue_camera_id, zone_id in QUEUE_CAMERAS:
                queue_length = rng.randint(0, 9)
                analytics_service.process_queue_reading(queue_camera_id, zone_id, queue_length)

            print(f"tick {tick} ok")
            if duration_seconds is not None and (time.monotonic() - start) >= duration_seconds:
                break
            time.sleep(tick_seconds)
    except KeyboardInterrupt:
        print("\nDemo stopped.")

    return tick


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the continuous retail-AI demo data generator.")
    parser.add_argument("--duration-seconds", type=float, default=None, help="Stop after N seconds (default: run until Ctrl+C)")
    parser.add_argument("--tick-seconds", type=float, default=2.0, help="Seconds between ticks (default: 2.0)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for a reproducible run")
    args = parser.parse_args()
    run_demo(duration_seconds=args.duration_seconds, tick_seconds=args.tick_seconds, seed=args.seed)


if __name__ == "__main__":
    main()
