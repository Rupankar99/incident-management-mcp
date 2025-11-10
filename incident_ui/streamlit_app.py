import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh


API_BASE = "http://localhost:8000"
POLL_MS = 3000


st.set_page_config(page_title="Incident Dashboard", layout="wide")
st.title("🚨 Real-time Incident Dashboard (In-memory)")


refresh = st_autorefresh(interval=POLL_MS, limit=None, key="refresh")
limit = st.sidebar.slider("Rows to show", 10, 500, 100)


try:
    res = requests.get(f"{API_BASE}/incidents", params={"limit": limit})
    data = res.json()
except Exception as e:
    st.error(f"Error fetching data: {e}")
    data = []


if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values(by="created_at", ascending=False), use_container_width=True)
else:
    st.info("No incidents yet. Waiting for new data...")

st.caption(f"Auto-refresh every {POLL_MS/1000:.0f}s. Total refreshes: {refresh}")