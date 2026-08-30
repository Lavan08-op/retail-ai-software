"""config.loader tested against the project's real config/settings.yaml —
this file's whole job is to read that exact file correctly, so testing
against a separate fixture would miss the point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.loader import (  # noqa: E402
    load_alert_cooldowns,
    load_alert_thresholds,
    load_camera_zone_map,
    load_settings,
)


def test_load_settings_returns_dict_with_expected_top_level_keys():
    settings = load_settings()
    assert "cameras" in settings
    assert "alert_thresholds" in settings
    assert "alert_cooldown_seconds" in settings


def test_camera_zone_map_matches_real_settings_yaml():
    zone_map = load_camera_zone_map()
    assert zone_map["entry-cam"] == "entrance"
    assert zone_map["queue-cam-1"] == "checkout-1"
    assert zone_map["queue-cam-2"] == "checkout-2"
    assert zone_map["shelf-cam-1"] == "shelf-zone-1"


def test_alert_thresholds_match_real_settings_yaml():
    thresholds = load_alert_thresholds()
    assert thresholds["queue_length_warning"] == 5
    assert thresholds["queue_length_critical"] == 8
    assert thresholds["occupancy_warning_pct"] == 80
    assert thresholds["dwell_seconds_warning"] == 300


def test_alert_cooldowns_match_real_settings_yaml():
    cooldowns = load_alert_cooldowns()
    assert cooldowns["QUEUE_THRESHOLD_EXCEEDED"] == 60
    assert cooldowns["CAMERA_OFFLINE"] == 30
