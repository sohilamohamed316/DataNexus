"""
src/dashboard/components/results_table.py
============================================
Renders per-check validation results as a clean, color-coded table,
plus a severity-weighted pass/fail breakdown chart.

Reuses `score_breakdown()` from src.validator.score_calculator — that
function was already written and explicitly left as "no use yet
(streamlit dashboard)". This is that use.
"""

from typing import List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.validator.score_calculator import score_breakdown
from src.dashboard.style import (
    STATUS_COLORS, STATUS_EMOJI, SEVERITY_COLORS, SEVERITY_EMOJI,
)


def render_results_table(results_df: pd.DataFrame) -> None:
    """Render validation_results rows as a readable, color-coded table."""
    if results_df.empty:
        st.info("No per-check results recorded for this run.")
        return

    display = results_df.copy()
    display["status"] = display["status"].apply(
        lambda s: f"{STATUS_EMOJI.get(str(s).lower(), '•')} {str(s).upper()}"
    )
    display["severity"] = display["severity"].apply(
        lambda s: f"{SEVERITY_EMOJI.get(str(s).lower(), '⚪')} {str(s).upper()}"
    )
    display["rows"] = display.apply(
        lambda r: f"{int(r['failing_rows'] or 0)} / {int(r['total_rows'] or 0)} failed"
        if pd.notnull(r.get("total_rows")) else "—",
        axis=1,
    )

    cols = ["check_name", "column_name", "check_type", "status", "severity",
            "rows", "expected_value", "actual_value"]
    cols = [c for c in cols if c in display.columns]

    st.dataframe(
        display[cols].rename(columns={
            "check_name": "Check", "column_name": "Column", "check_type": "Type",
            "status": "Status", "severity": "Severity", "rows": "Rows",
            "expected_value": "Expected", "actual_value": "Actual",
        }),
        use_container_width=True,
        hide_index=True,
    )

    failed = results_df[results_df["status"].str.lower().isin(["fail", "error"])]
    if not failed.empty:
        with st.expander(f"⚠️ Error details for {len(failed)} failed/errored check(s)"):
            for _, row in failed.iterrows():
                if row.get("error_message"):
                    st.code(f"{row['check_name']}: {row['error_message']}", language="text")


def render_severity_breakdown(results: List[dict]) -> go.Figure:
    """
    Stacked bar of passed vs failed checks per severity, using the
    same score_breakdown() the Validation Engine's weighting is based on.
    """
    breakdown = score_breakdown(results)
    severities = ["critical", "high", "medium", "low"]

    passed = [breakdown["by_severity"][s]["passed"] for s in severities]
    failed = [breakdown["by_severity"][s]["total"] - breakdown["by_severity"][s]["passed"]
              for s in severities]

    fig = go.Figure()
    fig.add_bar(
        name="Passed", x=[s.upper() for s in severities], y=passed,
        marker_color="#34D399",
    )
    fig.add_bar(
        name="Failed / Error", x=[s.upper() for s in severities], y=failed,
        marker_color="#F87171",
    )
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#E5E7EB"},
        height=280,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(title="Severity", gridcolor="#1F2937"),
        yaxis=dict(title="Check count", gridcolor="#1F2937"),
    )
    return fig
