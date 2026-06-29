"""
src/dashboard/views/trends.py
================================
Quality Score trend over time — filterable by dataset.
"""

import plotly.graph_objects as go
import streamlit as st

from src.dashboard import db
from src.dashboard.style import page_header, section, empty_state


def render() -> None:
    page_header("📈", "Quality Trends", "Track quality score drift over time, dataset by dataset.")

    datasets = db.get_datasets()
    if datasets.empty:
        empty_state("No datasets registered yet. Run <code>datanexus seed</code> first.")
        return

    ds_options = {"All datasets": None}
    ds_options.update({
        f"{row.table_name} ({row.source_name})": row.dataset_id
        for row in datasets.itertuples()
    })
    choice = st.selectbox("Dataset", list(ds_options.keys()))
    dataset_id = ds_options[choice]

    trend = db.get_quality_trend(dataset_id=dataset_id, limit=500)
    if trend.empty:
        empty_state(
            "No runs recorded for this filter yet.<br/>"
            "Trigger a run from the Overview page to start building history."
        )
        return

    section("Quality Score Over Time")
    fig = go.Figure()

    if dataset_id is None:
        for name, grp in trend.groupby("dataset_name"):
            grp = grp.sort_values("created_at")
            fig.add_trace(go.Scatter(
                x=grp["created_at"], y=grp["quality_score"],
                mode="lines+markers", name=name or "Unknown",
                line=dict(width=2.5), marker=dict(size=6),
            ))
    else:
        grp = trend.sort_values("created_at")
        fig.add_trace(go.Scatter(
            x=grp["created_at"], y=grp["quality_score"],
            mode="lines+markers", name="Quality Score",
            line=dict(width=3, color="#22D3EE"), marker=dict(size=7),
            fill="tozeroy", fillcolor="rgba(34,211,238,0.08)",
        ))
        thresholds = grp["quality_threshold"].dropna().unique()
        if len(thresholds) > 0:
            fig.add_hline(
                y=float(thresholds[-1]) * 100,
                line_dash="dash", line_color="#FBBF24",
                annotation_text="Pass threshold", annotation_position="top left",
            )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#E5E7EB"},
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Quality Score", range=[0, 105], gridcolor="#1F2937"),
        xaxis=dict(title="Run time", gridcolor="#1F2937"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    section("Pass / Fail / Error Mix")
    status_counts = (
        trend.groupby([trend["created_at"].dt.date, "status"]).size().reset_index(name="count")
    )
    status_colors = {"pass": "#34D399", "fail": "#F87171", "error": "#FBBF24",
                      "pending": "#64748B", "running": "#60A5FA"}

    fig2 = go.Figure()
    for status, color in status_colors.items():
        sub = status_counts[status_counts["status"] == status]
        if sub.empty:
            continue
        fig2.add_bar(x=sub["created_at"], y=sub["count"], name=status.upper(), marker_color=color)

    fig2.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#E5E7EB"},
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Date", gridcolor="#1F2937"),
        yaxis=dict(title="Run count", gridcolor="#1F2937"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig2, use_container_width=True)
