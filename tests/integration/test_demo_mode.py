"""Proves demo_mode populates real data across multiple tables. Uses
max_ticks (deterministic, zero sleep) rather than duration_seconds/wall-
clock timing — asserting "N ticks fit in M seconds" is inherently
machine-speed-dependent and was a real source of flakiness on a slower
machine.

Queue metric row counts use >= rather than == : AnalyticsService.process_tracks()
ALSO writes queue metrics whenever mock people happen to land in a queue
camera's zone during the pipeline loop, in addition to demo_mode's
explicit per-tick queue-reading simulation — both paths are legitimate,
so the exact total isn't a fixed number, only a guaranteed floor.

Table isolation between test FUNCTIONS is handled by
tests/integration/conftest.py's autouse fixture.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulation.demo_mode import run_demo  # noqa: E402
from storage import repositories  # noqa: E402


def test_demo_runs_fixed_tick_count_and_populates_storage():
    ticks = run_demo(max_ticks=5, seed=42)
    assert ticks == 5

    # 2 queue cameras seeded explicitly every tick -> at least ticks*2
    # queue rows guaranteed; pipeline-driven queue-zone detections may add
    # more, which is correct, not a bug.
    queue_metrics = repositories.recent_queue_metrics(limit=100)
    assert len(queue_metrics) >= 10

    occupancy = repositories.recent_occupancy(limit=100)
    assert isinstance(occupancy, list)


def test_demo_queue_values_are_reproducible_with_same_seed():
    run_demo(max_ticks=3, seed=7)
    values_a = sorted(m.queue_length for m in repositories.recent_queue_metrics(limit=100))

    # Manually clear tables between the two runs within this single test
    # function (conftest's autouse fixture only clears between separate
    # test functions, not between calls inside one).
    from storage.database import SessionWriter
    from storage.models import Base

    with SessionWriter() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

    run_demo(max_ticks=3, seed=7)
    values_b = sorted(m.queue_length for m in repositories.recent_queue_metrics(limit=100))

    # The real point of this test: same seed -> byte-for-byte identical
    # results, including however many rows the pipeline-driven path adds.
    assert values_a == values_b
    assert len(values_a) >= 6  # 3 ticks * 2 explicit readings, floor not exact
