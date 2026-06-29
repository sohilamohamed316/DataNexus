"""
src/dashboard/app.py
======================
DataNexus Dashboard — entry point / router.

Run with:
    streamlit run src/dashboard/app.py

This script no longer holds page content directly — each page lives
in src/dashboard/views/ as a `render()` function, and this file wires
them together with st.navigation(), which gives us grouped sidebar
sections + per-page icons + a default landing page, instead of the
flat, ungrouped list Streamlit's old auto pages/ folder produced.
"""

import sys
from pathlib import Path

# Make the project root importable, the same way src/cli/main.py does,
# since `streamlit run` only puts this script's own folder on sys.path.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from src.dashboard import db
from src.dashboard.style import inject_theme, sidebar_brand
from src.dashboard.utils import relative_time
from src.dashboard.views import overview, trends, run_details, data_profile, alerts, config_explorer

st.set_page_config(
    page_title="DataNexus — Data Quality Observatory",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

# ── Sidebar branding + live status, rendered above the nav menu ─────────────
with st.sidebar:
    db_alive = db.check_db_alive()
    recent = db.get_recent_runs(limit=1)
    last_run_text = (
        relative_time(recent.iloc[0]["created_at"]) if not recent.empty else "never"
    )
    kpis = db.get_overview_kpis() if db_alive else {"open_alerts": 0}
    sidebar_brand(db_alive, last_run_text, kpis.get("open_alerts", 0))

# ── Navigation, grouped into sections ────────────────────────────────────────
pg = st.navigation(
    {
        "Monitor": [
            st.Page(overview.render, title="Overview", icon="🛰️", default=True, url_path="overview"),
            st.Page(trends.render, title="Trends", icon="📈", url_path="trends"),
            st.Page(run_details.render, title="Run Details", icon="🔍", url_path="run-details"),
            st.Page(data_profile.render, title="Data Profile", icon="🧬", url_path="data-profile"),
        ],
        "Operate": [
            st.Page(alerts.render, title="Alerts", icon="🚨", url_path="alerts"),
            st.Page(config_explorer.render, title="Config Explorer", icon="📝", url_path="config-explorer"),
        ],
    }
)
pg.run()

with st.sidebar:
    st.markdown(
        '<div style="color:#4B5563; font-size:0.72rem; margin-top:18px;">'
        "DataNexus · DEPI 2026 Graduation Project</div>",
        unsafe_allow_html=True,
    )
