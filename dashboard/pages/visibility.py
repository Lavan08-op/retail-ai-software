import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Visibility", layout="wide")
st.title("Visibility")
st.caption("A relative score per zone, for comparing zones against each other — not a physical unit.")

metrics = repositories.recent_visibility_metrics(limit=100)

if not metrics:
    st.info("No visibility data yet — run the pipeline demo (with a camera->zone map) to populate data.")
else:
    st.dataframe(
        [{"zone_id": m.zone_id, "metric_name": m.metric_name, "value": m.value, "timestamp": m.timestamp} for m in metrics],
        use_container_width=True,
    )

    latest_by_zone: dict[str, float] = {}
    for m in metrics:
        zone = m.zone_id or "unassigned"
        latest_by_zone.setdefault(zone, m.value)

    st.subheader("Latest visibility score per zone")
    st.table(
        [{"zone_id": zone, "visibility_score": score} for zone, score in sorted(latest_by_zone.items())]
    )
