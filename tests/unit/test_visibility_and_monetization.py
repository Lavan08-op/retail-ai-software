"""Visibility and monetization analytics tested directly — pure functions,
no state, no Track objects needed at all."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analytics.monetization import compute_opportunity_score  # noqa: E402
from analytics.visibility import compute_visibility_score  # noqa: E402


def test_visibility_score_basic():
    result = compute_visibility_score("shelf-zone-1", traffic_count=10, avg_dwell_seconds=50)
    assert result.metric_name == "visibility_score"
    assert result.zone_id == "shelf-zone-1"
    # 0.6*10 + 0.4*(50/10) = 6 + 2 = 8
    assert result.value == 8.0


def test_visibility_score_zero_traffic_and_dwell():
    result = compute_visibility_score("shelf-zone-1", traffic_count=0, avg_dwell_seconds=0)
    assert result.value == 0.0


def test_opportunity_score_basic():
    result = compute_opportunity_score("shelf-zone-1", visibility_score=8.0, traffic_count=10)
    assert result.metric_name == "monetization_opportunity_score"
    # 0.5*8 + 0.5*10 = 4 + 5 = 9
    assert result.value == 9.0
    assert result.metadata["is_estimate"] is True


def test_opportunity_score_never_labeled_as_revenue():
    result = compute_opportunity_score("shelf-zone-1", visibility_score=5.0, traffic_count=5)
    assert "revenue" not in result.metric_name.lower()
    assert result.metadata["is_estimate"] is True
