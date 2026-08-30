import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from file_management import exporters  # noqa: E402

st.set_page_config(page_title="Reports", layout="wide")
st.title("Reports & Exports")
st.caption("Exports are read-only snapshots of the database — generating one never writes back to it.")

fmt = st.radio("Format", ["csv", "json"], horizontal=True)

EXPORTERS = {
    "Queue metrics": exporters.export_queue_metrics,
    "Occupancy": exporters.export_occupancy,
    "Active alerts": exporters.export_alerts,
    "Recent events": exporters.export_events,
}

for label, export_fn in EXPORTERS.items():
    if st.button(f"Generate {label} export ({fmt})"):
        path = export_fn(fmt=fmt)
        st.download_button(
            f"Download {path.name}",
            data=path.read_bytes(),
            file_name=path.name,
            key=f"download_{path.name}",
        )
