import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Queue", layout="wide")
st.title("Queue")

readings = repositories.recent_queue_metrics(limit=100)

if not readings:
    st.info("No queue data yet — run the pipeline demo to populate data.")
else:
    st.dataframe(
        [
            {
                "camera_id": r.camera_id,
                "zone_id": r.zone_id,
                "queue_length": r.queue_length,
                "avg_wait_seconds": r.avg_wait_seconds,
                "timestamp": r.timestamp,
            }
            for r in readings
        ],
        use_container_width=True,
    )

    latest_by_zone: dict[str, int] = {}
    for r in readings:  # readings ordered newest-first, so first hit per zone is latest
        zone = r.zone_id or "unassigned"
        latest_by_zone.setdefault(zone, r.queue_length)

    st.subheader("Latest queue length per zone")
    st.table(
        [{"zone_id": zone, "queue_length": length} for zone, length in sorted(latest_by_zone.items())]
    )
