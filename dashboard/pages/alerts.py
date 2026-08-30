import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Alerts", layout="wide")
st.title("Alerts")

alerts = repositories.active_alerts()

if not alerts:
    st.success("No active alerts.")
else:
    severity_counts: dict[str, int] = {}
    for a in alerts:
        severity_counts[a.severity] = severity_counts.get(a.severity, 0) + 1

    cols = st.columns(len(severity_counts) or 1)
    for col, (severity, count) in zip(cols, sorted(severity_counts.items())):
        col.metric(severity, count)

    st.subheader("Active alerts")
    st.dataframe(
        [
            {
                "type": a.event_type,
                "severity": a.severity,
                "camera": a.camera_id,
                "zone": a.zone_id,
                "message": a.message,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in alerts
        ],
        use_container_width=True,
    )
