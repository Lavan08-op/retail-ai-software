"""Streamlit entrypoint. Run with (from the project root, venv active):

    streamlit run dashboard/app.py

Only imports storage.repositories (read-only, sanctioned per that
module's own docstring) — never storage.writer. No business logic lives
here or in any dashboard/pages/ file; every number shown is either a
stored value or a trivial display transform (a max, a sum for a table)
of stored values, never a decision.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Retail Intelligence Platform", layout="wide")

st.title("Retail Intelligence Platform")
st.caption("Local-first, zero-cloud retail analytics — SIH prototype")

st.markdown(
    "Use the sidebar to navigate: **Overview**, **Traffic**, **Occupancy**, "
    "**Queue**, **Shelf**, **Visibility**, **Monetization**, **Alerts**, **Reports**."
)

cameras = repositories.list_cameras()
online = sum(1 for c in cameras if c.online)

col1, col2 = st.columns(2)
col1.metric("Cameras registered", len(cameras))
col2.metric("Cameras online", online)

if cameras:
    st.subheader("Cameras")
    st.dataframe(
        [{"id": c.id, "label": c.label, "zone_id": c.zone_id, "online": c.online} for c in cameras],
        use_container_width=True,
    )
else:
    st.info("No cameras registered yet — run the pipeline demo to populate data.")
