"""Monetization analytics — pure Python business logic. Produces an
estimated opportunity score from visibility and traffic signals.

This is deliberately NOT labeled as revenue anywhere — it's a relative
estimate of shelf/zone exposure value, only meaningful for comparing
zones against each other unless real sales data is layered in later
(metadata always carries is_estimate=True as a reminder downstream).
"""

from __future__ import annotations

from core.models import AnalyticsResult


def compute_opportunity_score(
    zone_id: str,
    visibility_score: float,
    traffic_count: int,
    exposure_weight: float = 0.5,
    traffic_weight: float = 0.5,
) -> AnalyticsResult:
    score = exposure_weight * visibility_score + traffic_weight * traffic_count
    return AnalyticsResult(
        metric_name="monetization_opportunity_score",
        zone_id=zone_id,
        value=round(score, 2),
        metadata={
            "visibility_score": visibility_score,
            "traffic_count": traffic_count,
            "is_estimate": True,
        },
    )
