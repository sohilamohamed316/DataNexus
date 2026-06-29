"""
src/dashboard/views/data_profile.py
=======================================
Surfaces ProfilerEngine's output. This data has existed in the
data_profiles table since Step 3, but nothing in the system displayed
it until now — every profiling run was effectively invisible.

Shows: row/column counts, per-column null %, distinct count,
min/max/mean/median for numeric columns, and detected pattern
(email/phone/date) badges. Profiles are currently produced as a
side-effect of running a validation (the engine profiles, then
validates) — there's no standalone "profile only" schedule yet,
so this page always shows the most recent profile on record.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import db
from src.dashboard.style import page_header, section, empty_state
from src.dashboard.utils import relative_time


def render() -> None:
    page_header("🧬", "Data Profile", "Column-level statistics captured by the Data Profiler.")

    datasets = db.get_datasets()
    if datasets.empty:
        empty_state("No datasets registered yet. Run <code>datanexus seed</code> first.")
        return

    ds_options = {
        f"{row.table_name} ({row.source_name})": row.dataset_id
        for row in datasets.itertuples()
    }
    choice = st.selectbox("Dataset", list(ds_options.keys()))
    dataset_id = ds_options[choice]

    profile_row, columns = db.get_latest_profile(dataset_id)

    if profile_row is None:
        empty_state(
            "No profile recorded for this dataset yet.<br/>"
            "Profiles are captured automatically the next time a validation run executes."
        )
        return

    k1, k2, k3 = st.columns(3)
    k1.metric("Row count", f"{int(profile_row['row_count']):,}")
    k2.metric("Column count", int(profile_row["column_count"]))
    k3.metric("Profiled", relative_time(profile_row["profiled_at"]))

    st.write("")
    section("Null % by Column")

    if columns:
        null_df = pd.DataFrame([
            {"column": name, "null_pct": stats.get("null_pct", 0) or 0}
            for name, stats in columns.items()
        ]).sort_values("null_pct", ascending=False)

        fig = go.Figure(go.Bar(
            x=null_df["null_pct"], y=null_df["column"], orientation="h",
            marker_color=["#F87171" if v > 20 else "#FBBF24" if v > 0 else "#34D399"
                          for v in null_df["null_pct"]],
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#E5E7EB"},
            height=max(220, 36 * len(null_df)),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title="Null %", range=[0, 100], gridcolor="#1F2937"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.write("")
    section("Per-Column Detail")

    if not columns:
        st.caption("No per-column statistics stored for this profile.")
        return

    rows = []
    for name, stats in columns.items():
        rows.append({
            "Column": name,
            "Null %": f"{stats.get('null_pct', 0):.1f}%" if stats.get("null_pct") is not None else "—",
            "Distinct": stats.get("distinct_count", "—"),
            "Min": stats.get("min", "—"),
            "Max": stats.get("max", "—"),
            "Mean": round(stats["mean"], 2) if isinstance(stats.get("mean"), (int, float)) else "—",
            "Median": stats.get("median", "—"),
            "Pattern": stats.get("detected_pattern") or "—",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("📋 Sample values (first detected per column)"):
        for name, stats in columns.items():
            samples = stats.get("sample_values")
            if samples:
                st.markdown(f"**{name}**: `{', '.join(str(s) for s in samples[:5])}`")
