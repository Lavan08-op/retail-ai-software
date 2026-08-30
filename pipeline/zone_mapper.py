"""Maps each Track's camera_id to a zone_id using a static camera->zone
map (typically config.loader.load_camera_zone_map() from
config/settings.yaml's `cameras:` list).

Deliberately NOT the tracker's job: the Tracker Protocol (mock now, the
teammate's real one later) only knows about detections and identity, not
store layout. Zone assignment is a business-logic concern that belongs
between the tracker and the analytics service — so it lives in pipeline/,
the layer that already sits at that exact seam.
"""

from __future__ import annotations

from core.models import Track


def assign_zones(tracks: list[Track], camera_zone_map: dict[str, str]) -> list[Track]:
    """Returns new Track objects with zone_id filled in from
    camera_zone_map. A camera_id not present in the map is left
    untouched (existing zone_id, usually None, passes through)."""
    zoned: list[Track] = []
    for t in tracks:
        zone_id = camera_zone_map.get(t.camera_id, t.zone_id)
        if zone_id == t.zone_id:
            zoned.append(t)
        else:
            zoned.append(t.model_copy(update={"zone_id": zone_id}))
    return zoned
