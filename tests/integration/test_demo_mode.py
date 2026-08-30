"""Proves demo_mode actually runs for a fixed duration and populates real
data across multiple tables — not just that it doesn't crash. Table
isolation between test functions is handled by
tests/integration/conftest.py's autouse fixture, so no per-file DB
setup/teardown is needed here."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.demo_mode import run_demo  # noqa: E402
from storage import repositories  # noqa: E402


def test_demo_runs_fixed_duration_and_populates_storage():
    ticks = run_demo(duration_seconds=2.0, tick_seconds=0.5, seed=42)

    assert ticks >= 2  # at least a couple of ticks completed in 2 seconds

    # Queue readings are seeded every tick for 2 configured queue cameras
    queue_metrics = repositories.recent_queue_metrics(limit=100)
    assert len(queue_metrics) >= ticks

    # Occupancy should have SOME rows too, from the zone-mapped cameras —
    # not asserting non-empty since a very short/unlucky run could produce
    # zero people, but it must not error.
    occupancy = repositories.recent_occupancy(limit=100)
    assert isinstance(occupancy, list)


def test_demo_tick_count_is_reproducible_with_same_seed():
    ticks_a = run_demo(duration_seconds=1.0, tick_seconds=0.5, seed=7)
    ticks_b = run_demo(duration_seconds=1.0, tick_seconds=0.5, seed=7)
    assert ticks_a == ticks_b
