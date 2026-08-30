import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from storage import repositories  # noqa: E402

st.set_page_config(page_title="Traffic", layout="wide")
st.title("Traffic — Entry / Exit")
st.caption("Last 24 hours")

counts = repositories.entry_exit_counts()

col1, col2 = st.columns(2)
col1.metric("Entries (in)", counts.get("in", 0))
col2.metric("Exits (out)", counts.get("out", 0))

if not counts.get("in") and not counts.get("out"):
    st.info("No entry/exit events recorded yet — run the pipeline demo to populate data.")
