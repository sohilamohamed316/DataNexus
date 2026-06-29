"""
src/dashboard/views/run_details.py
=====================================
Drill into a single ValidationRun: status card, quality gauge,
severity-weighted breakdown, and the full per-check results table.
"""

import streamlit as st

from src.dashboard import db
from src.dashboard.style import page_header, section, status_pill_html, empty_state
from src.dashboard.components.score_gauge import render_score_gauge
from src.dashboard.components.results_table import render_results_table, render_severity_breakdown


def render() -> None:
    page_header("🔍", "Run Details", "Inspect exactly what happened during one validation run.")

    recent_runs = db.get_recent_runs(limit=100)
    if recent_runs.empty:
        empty_state("No runs recorded yet. Trigger one from the Overview page.")
        return

    run_labels = {
        f"#{int(r.run_id)} · {r.dataset_name or 'unknown'} · {r.status.upper()} "
        f"({r.created_at:%Y-%m-%d %H:%M})": int(r.run_id)
        for r in recent_runs.itertuples()
    }

    default_idx = 0
    last_triggered = st.session_state.get("_last_triggered_run")
    labels_list = list(run_labels.keys())
    if last_triggered is not None:
        for i, lbl in enumerate(labels_list):
            if run_labels[lbl] == last_triggered:
                default_idx = i
                break

    choice = st.selectbox("Select a run", labels_list, index=default_idx)
    run_id = run_labels[choice]

    run_row, results_df = db.get_run_detail(run_id)
    if run_row is None:
        empty_state("That run could not be found — it may have been deleted.")
        return

    c1, c2, c3 = st.columns([1, 1, 1.6])

    with c1:
        fig = render_score_gauge(
            run_row["quality_score"],
            title="Quality Score",
            threshold=(run_row["quality_threshold"] or 0) * 100
            if run_row["quality_threshold"] is not None else None,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(f"**Run** `#{run_row['run_id']}`")
        st.markdown(status_pill_html(run_row["status"]), unsafe_allow_html=True)
        st.write("")
        st.markdown(f"**Dataset:** {run_row['dataset_name'] or '—'}")
        st.markdown(f"**Config:** {run_row['config_name'] or '—'} (id={run_row['config_id']})")
        st.markdown(f"**Triggered by:** `{run_row['triggered_by'] or '—'}`")
        if run_row.get("started_at") is not None and run_row.get("finished_at") is not None:
            try:
                duration = (run_row["finished_at"] - run_row["started_at"]).total_seconds()
                st.markdown(f"**Duration:** {duration:.2f}s")
            except Exception:
                pass
        if run_row.get("error_message"):
            st.error(run_row["error_message"][:400])

    with c3:
        section("Severity-Weighted Breakdown")
        if not results_df.empty:
            results_for_score = [
                {"status": r["status"], "severity": r["severity"]}
                for _, r in results_df.iterrows()
            ]
            chart = render_severity_breakdown(results_for_score)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.caption("No per-check results to break down for this run.")

    st.write("")
    header_col, dl_col = st.columns([4, 1])
    with header_col:
        section("Per-Check Results")
    with dl_col:
        if not results_df.empty:
            st.download_button(
                "⬇️ Export CSV",
                data=results_df.to_csv(index=False).encode("utf-8"),
                file_name=f"run_{run_id}_results.csv",
                mime="text/csv",
                use_container_width=True,
            )

    render_results_table(results_df)
