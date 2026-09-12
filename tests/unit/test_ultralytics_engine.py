from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from adapters.inference.ultralytics_engine import UltralyticsInferenceEngine
from core.frame_data import FrameData
from core.models import Frame


class _Boxes:
    xyxy = [[1, 2, 11, 22]]
    cls = [0]
    conf = [0.91]


class _Model:
    names = {0: "person"}

    def predict(self, **kwargs):
        assert kwargs["source"].shape == (24, 32, 3)
        return [SimpleNamespace(boxes=_Boxes(), names=self.names)]


def test_ultralytics_adapter_maps_model_result_to_detection():
    frame = FrameData(
        metadata=Frame(camera_id="entry-cam", width=32, height=24),
        image=np.zeros((24, 32, 3), dtype=np.uint8),
    )

    detections = UltralyticsInferenceEngine(model=_Model()).infer(frame)

    assert len(detections) == 1
    assert detections[0].camera_id == "entry-cam"
    assert detections[0].class_name == "person"
    assert detections[0].bbox == (1.0, 2.0, 11.0, 22.0)
    assert detections[0].confidence == 0.91
