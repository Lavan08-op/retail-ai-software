"""Ultralytics YOLO adapter for live StoreSense frames."""

from __future__ import annotations

from typing import Any

from core.frame_data import FrameData
from core.models import Detection


class UltralyticsInferenceEngine:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence: float = 0.35,
        classes: list[int] | None = None,
        model: Any | None = None,
    ) -> None:
        if model is None:
            try:
                from ultralytics import YOLO
            except ImportError as error:
                raise RuntimeError("Ultralytics is required for live YOLO inference") from error
            model = YOLO(model_path)
        self._model = model
        self._confidence = confidence
        self._classes = classes

    def infer(self, frame_data: FrameData) -> list[Detection]:
        results = self._model.predict(
            source=frame_data.image,
            conf=self._confidence,
            classes=self._classes,
            device="cpu",
            verbose=False,
        )
        if not results or getattr(results[0], "boxes", None) is None:
            return []
        detections = []
        boxes = results[0].boxes
        names = getattr(results[0], "names", getattr(self._model, "names", {}))
        for index, coordinates in enumerate(boxes.xyxy):
            class_id = int(boxes.cls[index])
            confidence = float(boxes.conf[index])
            values = [float(value) for value in coordinates]
            detections.append(
                Detection(
                    camera_id=frame_data.metadata.camera_id,
                    class_id=class_id,
                    class_name=str(names[class_id]),
                    confidence=confidence,
                    bbox=(values[0], values[1], values[2], values[3]),
                )
            )
        return detections
