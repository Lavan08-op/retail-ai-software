"""Occupancy analytics — pure Python business logic. Computes current
headcount per zone from Track objects and tracks each zone's peak-so-far
in memory. Zone capacities are passed in by the caller (eventually loaded
from config/settings.yaml) — never hardcoded here.

Note: this only produces results for tracks that carry a zone_id. Today's
mock tracker never sets one (real zone assignment is a later integration
step — either from the teammate's tracker or a zone-mapping layer), so
this module is architecture-ready but will emit nothing until zone_id is
actually populated upstream. That's expected, not a bug.
"""

from __future__ import annotations

from collections import defaultdict

from core.models import AnalyticsResult, Track


class OccupancyTracker:
    def __init__(
        self,
        zone_capacities: dict[str, int] | None = None,
        class_name: str = "person",
    ):
        self._capacities = zone_capacities or {}
        self._class_name = class_name
        self._peak: dict[str, int] = defaultdict(int)

    def update(self, tracks: list[Track]) -> list[AnalyticsResult]:
        per_zone: dict[str, int] = defaultdict(int)
        for t in tracks:
            if t.class_name == self._class_name and t.zone_id:
                per_zone[t.zone_id] += 1

        results: list[AnalyticsResult] = []
        for zone_id, count in per_zone.items():
            self._peak[zone_id] = max(self._peak[zone_id], count)
            capacity = self._capacities.get(zone_id)
            pct = (count / capacity * 100) if capacity else None
            results.append(
                AnalyticsResult(
                    metric_name="occupancy_current",
                    zone_id=zone_id,
                    value=float(count),
                    unit="people",
                    metadata={"peak": self._peak[zone_id], "capacity": capacity, "pct": pct},
                )
            )
        return results

    def peak(self, zone_id: str) -> int:
        return self._peak.get(zone_id, 0)
