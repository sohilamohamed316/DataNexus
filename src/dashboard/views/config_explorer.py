"""
src/dashboard/views/config_explorer.py
==========================================
Browse every ValidationConfig: target dataset, parsed checks (via the
real ConfigParser), raw YAML, and an active/inactive toggle.

Intentionally a viewer + lightweight toggle, not a full create/edit
UI — see the dashboard design discussion: full config management is
deferred until the REST API (Step 8) exists, so there's a single
validated write path shared by the CLI, API, and dashboard.
"""

import pandas as pd
import streamlit as st

from src.dashboard import db
from src.dashboard.style import page_header, section, severity_pill_html, empty_state


def render() -> None:
    page_header("📝", "Config Explorer", "Every validation config, its target dataset, and its rules.")

    configs = db.get_configs()
    if configs.empty:
        empty_state(
            "No validation configs found.<br/>"
            "Run <code>datanexus seed</code> to create the demo configs."
        )
        return

    active_count = int(configs["is_active"].sum())
    st.caption(f"{len(configs)} config(s) total · {active_count} active")

    for row in configs.itertuples():
        status_dot = "🟢" if row.is_active else "⚪"
        with st.expander(
            f"{status_dot}  #{row.id} · {row.name}  —  {row.dataset_name or 'unknown dataset'}",
            expanded=False,
        ):
            meta_cols = st.columns(4)
            meta_cols[0].markdown(f"**Source:** {row.source_name or '—'} ({row.source_type or '—'})")
            meta_cols[1].markdown(f"**Quality threshold:** {row.quality_threshold * 100:.0f}%")
            meta_cols[2].markdown(f"**Schedule:** `{row.schedule_cron or 'manual'}`")
            meta_cols[3].markdown(f"**Alert channels:** {row.alert_channels or '—'}")

            new_active = st.toggle("Active", value=bool(row.is_active), key=f"active_{row.id}")
            if new_active != bool(row.is_active):
                db.toggle_config_active(row.id, new_active)
                st.rerun()

            st.write("")
            section("Parsed Checks")
            try:
                from src.config_parser import from_string
                parsed = from_string(row.config_yaml)
                checks_df = pd.DataFrame([c.to_dict() for c in parsed.checks])
                checks_df["severity"] = checks_df["severity"].apply(severity_pill_html)
                cols = ["name", "check_type", "column", "severity", "threshold"]
                cols = [c for c in cols if c in checks_df.columns]
                st.write(
                    checks_df[cols].rename(columns={
                        "name": "Check", "check_type": "Type",
                        "column": "Column", "severity": "Severity", "threshold": "Threshold",
                    }).to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                st.warning(f"Could not parse this config's YAML: {exc}")

            st.write("")
            section("Raw YAML")
            st.code(row.config_yaml, language="yaml")
