"""Proves the mock adapter chain works end to end: video -> inference ->
tracker -> (optionally) event bus. No database, no real hardware, no
network — just the Protocols from interfaces/ satisfied by mocks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from adapters.inference.mock_inference_engine import MockInferenceEngine  # noqa: E402
from adapters.messaging.local_event_bus import LocalEventBus  # noqa: E402
from adapters.tracking.mock_tracker import MockTracker  # noqa: E402
from adapters.video.mock_video_source import MockVideoSource  # noqa: E402


def test_video_source_produces_frames():
    source = MockVideoSource("queue-cam-1")
    frame = source.get_frame()
    assert frame is not None
    assert frame.camera_id == "queue-cam-1"
    assert frame.frame_index == 1

    frame2 = source.get_frame()
    assert frame2.frame_index == 2
    assert source.is_connected() is True
    assert source.camera_id() == "queue-cam-1"


def test_inference_engine_returns_detections():
    source = MockVideoSource("queue-cam-1")
    engine = MockInferenceEngine(min_people=2, max_people=2, seed=42)
    frame = source.get_frame()
    detections = engine.infer(frame)

    assert len(detections) == 2
    assert all(d.class_name == "person" for d in detections)
    assert all(d.camera_id == "queue-cam-1" for d in detections)


def test_tracker_assigns_persistent_ids_across_calls():
    tracker = MockTracker()
    engine = MockInferenceEngine(min_people=2, max_people=2, seed=1)
    source = MockVideoSource("queue-cam-1")

    tracks1 = tracker.update(engine.infer(source.get_frame()))
    tracks2 = tracker.update(engine.infer(source.get_frame()))

    ids1 = {t.track_id for t in tracks1}
    ids2 = {t.track_id for t in tracks2}
    assert ids1 == ids2  # same 2 track IDs persist across the two calls
    assert len(tracks1) == 2
    assert len(tracks2) == 2


def test_full_mock_chain_video_to_tracks():
    source = MockVideoSource("entry-cam")
    engine = MockInferenceEngine(min_people=1, max_people=3, seed=7)
    tracker = MockTracker()

    tracks = tracker.update(engine.infer(source.get_frame()))

    assert isinstance(tracks, list)
    for t in tracks:
        assert t.camera_id == "entry-cam"
        assert t.class_name == "person"


def test_local_event_bus_publish_subscribe():
    bus = LocalEventBus()
    received = []

    bus.subscribe("test.topic", lambda payload: received.append(payload))
    bus.publish("test.topic", {"hello": "world"})

    assert received == [{"hello": "world"}]


def test_local_event_bus_ignores_unrelated_topics():
    bus = LocalEventBus()
    received = []
    bus.subscribe("topic.a", lambda p: received.append(p))
    bus.publish("topic.b", {"x": 1})
    assert received == []
