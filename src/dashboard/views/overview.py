"""
src/dashboard/views/overview.py
==================================
Overview page: fleet-wide KPIs, a live "run validation now" control,
and the most recent runs feed.
"""

import streamlit as st

from src.dashboard import db
from src.dashboard.style import page_header, section, status_pill_html, empty_state, ACCENT


def render() -> None:
    page_header(
        "🛰️",
        "Overview",
        "Automated profiling, validation, and alerting for your data pipelines.",
    )

    kpis = db.get_overview_kpis()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Datasets monitored", kpis["datasets"])
    k2.metric("Active configs", kpis["active_configs"])
    k3.metric("Total runs", kpis["total_runs"])
    k4.metric(
        "Avg. quality score",
        f"{kpis['avg_score']:.1f}" if kpis["avg_score"] is not None else "—",
        help="Average of the last 20 validation runs.",
    )
    k5.metric(
        "Open alerts",
        kpis["open_alerts"],
        delta=None if kpis["open_alerts"] == 0 else "needs attention",
        delta_color="inverse",
    )

    st.write("")

    left, right = st.columns([1, 1.4], gap="large")
    recent_runs = db.get_recent_runs(limit=15)

    with left:
        section("Latest Run")
        if recent_runs.empty:
            empty_state(
                "No validation runs yet.<br/>"
                "Run <code>datanexus seed</code> then <code>datanexus run &lt;config-id&gt;</code>, "
                "or trigger one from the panel on the right →"
            )
        else:
            from src.dashboard.components.score_gauge import render_score_gauge

            latest = recent_runs.iloc[0]
            fig = render_score_gauge(
                latest["quality_score"],
                title=f"{latest['dataset_name'] or 'Unknown dataset'}",
                threshold=(latest["quality_threshold"] or 0) * 100
                if latest["quality_threshold"] is not None else None,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(
                f"Run **#{int(latest['run_id'])}** · {status_pill_html(latest['status'])} "
                f"&nbsp;·&nbsp; triggered by `{latest['triggered_by'] or '—'}`",
                unsafe_allow_html=True,
            )

    with right:
        section("Run a Validation Now")
        configs = db.get_configs(active_only=True)

        if configs.empty:
            empty_state(
                "No active validation configs found.<br/>"
                "Seed demo data first: <code>datanexus seed</code>"
            )
        else:
            options = {
                f"#{row.id} · {row.name} ({row.dataset_name})": row.id
                for row in configs.itertuples()
            }
            choice = st.selectbox("Validation config", list(options.keys()))
            config_id = options[choice]

            st.caption(
                "Runs the real ValidationEngine against the live dataset — "
                "same code path the CLI uses."
            )

            if st.button("▶️  Run validation now", type="primary", use_container_width=True):
                with st.spinner("Running validation engine…"):
                    try:
                        from src.validator.validation_engine import ValidationEngine
                        run_id = ValidationEngine().run(config_id, triggered_by="dashboard")
                        db.clear_cache()
                        st.session_state["_last_triggered_run"] = run_id
                        st.success(f"✅ Run #{run_id} completed.")
                        st.balloons()
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Run failed: {exc}")

    st.write("")
    section("Recent Runs")

    if recent_runs.empty:
        empty_state("Nothing to show yet — trigger a run above to populate this feed.")
        return

    display = recent_runs.copy()
    display["Status"] = display["status"].apply(status_pill_html)
    display["Score"] = display["quality_score"].apply(
        lambda s: f"{s:.1f}" if s is not None else "—"
    )
    display["Run"] = display["run_id"].apply(lambda i: f"#{int(i)}")
    display["When"] = display["created_at"].dt.strftime("%Y-%m-%d %H:%M")

    table_df = display[[
        "Run", "dataset_name", "config_name", "Status", "Score", "triggered_by", "When",
    ]].rename(columns={
        "dataset_name": "Dataset", "config_name": "Config", "triggered_by": "Triggered by",
    })
    st.write(table_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="margin-top:28px; color:#6B7280; font-size:0.82rem;">
            Use the sidebar to open <b style="color:{ACCENT}">Trends</b>,
            <b style="color:{ACCENT}">Run Details</b>,
            <b style="color:{ACCENT}">Data Profile</b>,
            <b style="color:{ACCENT}">Alerts</b>, or the
            <b style="color:{ACCENT}">Config Explorer</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )
