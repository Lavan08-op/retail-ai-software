import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Overview", layout="wide")
st.title("Overview")

occupancy = repositories.recent_occupancy(limit=50)
alerts = repositories.active_alerts()
events = repositories.recent_events(limit=20)

col1, col2, col3 = st.columns(3)
col1.metric("Active alerts", len(alerts))
col2.metric("Occupancy readings (recent)", len(occupancy))
col3.metric(
    "Total current occupancy (sum of recent readings)",
    sum(o.current_count for o in occupancy),
)

st.subheader("Recent events")
if events:
    st.dataframe(
        [
            {
                "type": e.event_type,
                "severity": e.severity,
                "camera": e.camera_id,
                "zone": e.zone_id,
                "message": e.message,
                "time": e.timestamp,
            }
            for e in events
        ],
        use_container_width=True,
    )
else:
    st.info("No events recorded yet — run the pipeline demo to populate data.")
