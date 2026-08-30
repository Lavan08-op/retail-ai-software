"""Shared enums. Kept separate from models.py so both core/ and anything
importing only enums (e.g. config validation) don't have to pull in the full
Pydantic model set."""

from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventType(str, Enum):
    PERSON_ENTERED = "PERSON_ENTERED"
    PERSON_EXITED = "PERSON_EXITED"
    HIGH_OCCUPANCY = "HIGH_OCCUPANCY"
    QUEUE_THRESHOLD_EXCEEDED = "QUEUE_THRESHOLD_EXCEEDED"
    SHELF_ACTIVITY = "SHELF_ACTIVITY"
    VISIBILITY_THRESHOLD = "VISIBILITY_THRESHOLD"
    MONETIZATION_OPPORTUNITY = "MONETIZATION_OPPORTUNITY"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    STREAM_LOST = "STREAM_LOST"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class ZoneType(str, Enum):
    ENTRANCE = "entrance"
    AISLE = "aisle"
    CHECKOUT = "checkout"
    SHELF = "shelf"
