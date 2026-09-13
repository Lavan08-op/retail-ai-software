"""Smoke-test configured live phone camera streams before starting YOLO."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed with the base app
    load_dotenv = None

from adapters.video.opencv_rtsp_source import OpenCVRTSPVideoSource
from config.live_cameras import load_live_camera_urls

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


def check_camera(camera_id: str, url: str, attempts: int, delay_seconds: float) -> bool:
    source = OpenCVRTSPVideoSource(camera_id, url, reconnect_delay_seconds=0)
    try:
        for attempt in range(1, attempts + 1):
            frame = source.get_frame()
            if frame is not None:
                print(
                    f"[OK] {camera_id}: "
                    f"{frame.metadata.width}x{frame.metadata.height} "
                    f"frame {frame.metadata.frame_index} from {url}"
                )
                return True
            if attempt < attempts:
                time.sleep(delay_seconds)
        print(f"[FAIL] {camera_id}: no frame after {attempts} attempt(s) from {url}")
        return False
    finally:
        source.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read one frame from each configured live camera stream.")
    parser.add_argument("--attempts", type=int, default=5, help="Read attempts per camera.")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between attempts.")
    args = parser.parse_args()

    camera_urls = load_live_camera_urls()
    print(f"[CAMERAS] Checking {len(camera_urls)} configured stream(s)")
    results = [
        check_camera(camera_id, url, attempts=args.attempts, delay_seconds=args.delay)
        for camera_id, url in camera_urls.items()
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
