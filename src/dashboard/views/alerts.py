"""
src/dashboard/views/alerts.py
================================
Active alert inbox. Works against the `alerts` table directly — it
will naturally start filling in once Alert Manager (Step 7) starts
dispatching real notifications.
"""

import streamlit as st

from src.dashboard import db
from src.dashboard.style import page_header, section, severity_pill_html, empty_state


def render() -> None:
    page_header("🚨", "Alerts", "Notifications dispatched when a validation run fails its quality threshold.")

    alerts = db.get_alerts(limit=200)
    if alerts.empty:
        empty_state(
            "No alerts have been dispatched yet.<br/><br/>"
            "This table fills in automatically once <b>Alert Manager (Step 7)</b> is wired up "
            "and a validation run fails its quality threshold — nothing to configure here."
        )
        return

    show_only_open = st.toggle("Show only unacknowledged", value=True)
    view = alerts if not show_only_open else alerts[~alerts["acknowledged"]]

    if view.empty:
        empty_state("No alerts match this filter. 🎉 Everything's acknowledged.")
        return

    section(f"{len(view)} alert(s)")

    for _, row in view.iterrows():
        with st.container(border=True):
            top = st.columns([0.18, 0.5, 0.18, 0.14])
            top[0].markdown(severity_pill_html(row["severity"]), unsafe_allow_html=True)
            top[1].markdown(
                f"**{row['dataset_name'] or '—'}** · {row['config_name'] or '—'} "
                f"· run `#{int(row['run_id'])}`"
            )
            top[2].caption(f"via {row['channel']} · {row['created_at']:%Y-%m-%d %H:%M}")

            if not row["acknowledged"]:
                if top[3].button("Acknowledge", key=f"ack_{row['alert_id']}"):
                    db.acknowledge_alert(int(row["alert_id"]))
                    st.rerun()
            else:
                top[3].caption(f"✓ by {row['acknowledged_by'] or '—'}")

            st.write(row["message"])
