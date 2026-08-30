import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Shelf", layout="wide")
st.title("Shelf Activity")

events = repositories.recent_shelf_events(limit=50)

if not events:
    st.info("No shelf activity recorded yet — run the pipeline demo to populate data.")
else:
    st.dataframe(
        [
            {
                "camera_id": e.camera_id,
                "zone_id": e.zone_id,
                "event_label": e.event_label,
                "timestamp": e.timestamp,
            }
            for e in events
        ],
        use_container_width=True,
    )
