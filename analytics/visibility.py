"""Visibility analytics — pure Python business logic. Combines traffic and
average-dwell-time signals into a single visibility_score per zone.

Deliberately a relative score for comparing zones against each other, not
a physical unit of anything real — the weights below are a starting point,
meant to be tuned once real traffic numbers exist from an actual demo run.
"""

from __future__ import annotations

from core.models import AnalyticsResult


def compute_visibility_score(
    zone_id: str,
    traffic_count: int,
    avg_dwell_seconds: float,
    traffic_weight: float = 0.6,
    dwell_weight: float = 0.4,
) -> AnalyticsResult:
    score = traffic_weight * traffic_count + dwell_weight * (avg_dwell_seconds / 10.0)
    return AnalyticsResult(
        metric_name="visibility_score",
        zone_id=zone_id,
        value=round(score, 2),
        metadata={"traffic_count": traffic_count, "avg_dwell_seconds": avg_dwell_seconds},
    )
