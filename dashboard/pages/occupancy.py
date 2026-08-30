import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Occupancy", layout="wide")
st.title("Occupancy")

readings = repositories.recent_occupancy(limit=100)

if not readings:
    st.info("No occupancy data yet — run the pipeline demo to populate data.")
else:
    st.dataframe(
        [{"zone_id": r.zone_id, "current_count": r.current_count, "timestamp": r.timestamp} for r in readings],
        use_container_width=True,
    )

    peak_by_zone: dict[str, int] = {}
    for r in readings:
        zone = r.zone_id or "unassigned"
        peak_by_zone[zone] = max(peak_by_zone.get(zone, 0), r.current_count)

    st.subheader("Peak occupancy per zone (from recent readings)")
    st.table(
        [{"zone_id": zone, "peak_count": count} for zone, count in sorted(peak_by_zone.items())]
    )
