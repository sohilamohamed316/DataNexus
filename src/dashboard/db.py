"""
src/dashboard/db.py
====================
Shared, cached, read-only query layer for the Streamlit dashboard.

Design notes
------------
- The dashboard talks to PostgreSQL *directly* through the same
  SQLAlchemy `engine` the rest of DataNexus uses (src.database.engine).
  No REST API (Step 8) is required for the dashboard to function —
  it queries the database the same way the CLI does.
- Every read goes through `st.cache_data(ttl=...)` so navigating
  between pages doesn't re-hit Postgres on every rerun. Call
  `clear_cache()` after any write (triggering a run, acknowledging
  an alert, toggling a config) so the UI reflects the change.
- All functions return plain pandas DataFrames or dicts — no ORM
  objects leak past this module, which keeps every page simple.
"""

from datetime import datetime
import json
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.database import engine, get_db_session
from src.database.models import Alert, ValidationConfig


def clear_cache() -> None:
    st.cache_data.clear()


# ── Overview KPIs ────────────────────────────────────────────────────────────

@st.cache_data(ttl=10, show_spinner=False)
def get_overview_kpis() -> dict:
    with engine.connect() as conn:
        datasets       = conn.execute(text("SELECT COUNT(*) FROM datasets")).scalar() or 0
        active_configs = conn.execute(
            text("SELECT COUNT(*) FROM validation_configs WHERE is_active = TRUE")
        ).scalar() or 0
        total_runs = conn.execute(text("SELECT COUNT(*) FROM validation_runs")).scalar() or 0
        avg_score = conn.execute(
            text(
                """
                SELECT AVG(quality_score) FROM (
                    SELECT quality_score FROM validation_runs
                    WHERE quality_score IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 20
                ) recent
                """
            )
        ).scalar()
        open_alerts = conn.execute(
            text("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE")
        ).scalar() or 0

    return {
        "datasets": int(datasets),
        "active_configs": int(active_configs),
        "total_runs": int(total_runs),
        "avg_score": round(float(avg_score), 1) if avg_score is not None else None,
        "open_alerts": int(open_alerts),
    }


# ── Runs ──────────────────────────────────────────────────────────────────────

_RUNS_QUERY = """
    SELECT
        vr.id            AS run_id,
        vr.status        AS status,
        vr.quality_score AS quality_score,
        vr.triggered_by  AS triggered_by,
        vr.started_at    AS started_at,
        vr.finished_at   AS finished_at,
        vr.created_at    AS created_at,
        vr.error_message AS error_message,
        vc.id            AS config_id,
        vc.name          AS config_name,
        vc.quality_threshold AS quality_threshold,
        d.id             AS dataset_id,
        d.table_name     AS dataset_name,
        d.schema_name    AS schema_name,
        ds.name          AS source_name
    FROM validation_runs vr
    LEFT JOIN validation_configs vc ON vr.config_id = vc.id
    LEFT JOIN datasets d            ON vc.dataset_id = d.id
    LEFT JOIN data_sources ds       ON d.source_id = ds.id
    ORDER BY vr.created_at DESC
    LIMIT :limit
"""


@st.cache_data(ttl=10, show_spinner=False)
def get_recent_runs(limit: int = 50) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(text(_RUNS_QUERY), conn, params={"limit": limit})
    for col in ("started_at", "finished_at", "created_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


_RUN_BY_ID_QUERY = """
    SELECT
        vr.id            AS run_id,
        vr.status        AS status,
        vr.quality_score AS quality_score,
        vr.triggered_by  AS triggered_by,
        vr.started_at    AS started_at,
        vr.finished_at   AS finished_at,
        vr.created_at    AS created_at,
        vr.error_message AS error_message,
        vc.id            AS config_id,
        vc.name          AS config_name,
        vc.quality_threshold AS quality_threshold,
        d.id             AS dataset_id,
        d.table_name     AS dataset_name,
        d.schema_name    AS schema_name,
        ds.name          AS source_name
    FROM validation_runs vr
    LEFT JOIN validation_configs vc ON vr.config_id = vc.id
    LEFT JOIN datasets d            ON vc.dataset_id = d.id
    LEFT JOIN data_sources ds       ON d.source_id = ds.id
    WHERE vr.id = :run_id
"""


@st.cache_data(ttl=10, show_spinner=False)
def get_run_detail(run_id: int):
    """Returns (run_row: dict | None, results_df: pd.DataFrame)."""
    with engine.connect() as conn:
        run_df = pd.read_sql(text(_RUN_BY_ID_QUERY), conn, params={"run_id": run_id})
        results_df = pd.read_sql(
            text(
                """
                SELECT check_name, column_name, check_type, status, severity,
                       expected_value, actual_value, failing_rows, total_rows,
                       error_message, executed_at
                FROM validation_results
                WHERE run_id = :run_id
                ORDER BY executed_at ASC, id ASC
                """
            ),
            conn, params={"run_id": run_id},
        )
    run_row = run_df.iloc[0].to_dict() if not run_df.empty else None
    return run_row, results_df


# ── Trends ────────────────────────────────────────────────────────────────────

_TREND_BASE_QUERY = """
    SELECT
        vr.id            AS run_id,
        vr.status        AS status,
        vr.quality_score AS quality_score,
        vr.created_at    AS created_at,
        vc.id            AS config_id,
        vc.name          AS config_name,
        vc.quality_threshold AS quality_threshold,
        d.id             AS dataset_id,
        d.table_name     AS dataset_name
    FROM validation_runs vr
    LEFT JOIN validation_configs vc ON vr.config_id = vc.id
    LEFT JOIN datasets d            ON vc.dataset_id = d.id
"""


@st.cache_data(ttl=10, show_spinner=False)
def get_quality_trend(dataset_id: Optional[int] = None, limit: int = 200) -> pd.DataFrame:
    params = {"limit": limit}
    query = _TREND_BASE_QUERY
    if dataset_id is not None:
        query += " WHERE d.id = :dataset_id "
        params["dataset_id"] = dataset_id
    query += " ORDER BY vr.created_at ASC LIMIT :limit "

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


# ── Datasets / configs (for filters + the "run now" picker) ─────────────────

@st.cache_data(ttl=15, show_spinner=False)
def get_datasets() -> pd.DataFrame:
    query = """
        SELECT d.id AS dataset_id, d.table_name, d.schema_name,
               ds.name AS source_name, ds.source_type
        FROM datasets d
        LEFT JOIN data_sources ds ON d.source_id = ds.id
        ORDER BY d.table_name
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


@st.cache_data(ttl=15, show_spinner=False)
def get_configs(active_only: bool = False) -> pd.DataFrame:
    query = """
        SELECT vc.id, vc.name, vc.is_active, vc.quality_threshold,
               vc.schedule_cron, vc.alert_channels, vc.config_yaml,
               vc.created_at, vc.updated_at,
               d.id AS dataset_id, d.table_name AS dataset_name,
               ds.name AS source_name, ds.source_type
        FROM validation_configs vc
        LEFT JOIN datasets d      ON vc.dataset_id = d.id
        LEFT JOIN data_sources ds ON d.source_id   = ds.id
    """
    if active_only:
        query += " WHERE vc.is_active = TRUE "
    query += " ORDER BY vc.id ASC "
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def toggle_config_active(config_id: int, is_active: bool) -> None:
    with get_db_session() as session:
        cfg = session.query(ValidationConfig).filter_by(id=config_id).first()
        if cfg is not None:
            cfg.is_active = is_active
            cfg.updated_at = datetime.utcnow()
    clear_cache()


# ── Alerts ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=8, show_spinner=False)
def get_alerts(limit: int = 100) -> pd.DataFrame:
    query = """
        SELECT a.id AS alert_id, a.run_id, a.channel, a.alert_type, a.severity,
               a.message, a.status, a.acknowledged, a.acknowledged_by,
               a.acknowledged_at, a.sent_at, a.created_at,
               vc.name AS config_name, d.table_name AS dataset_name
        FROM alerts a
        LEFT JOIN validation_runs vr   ON a.run_id = vr.id
        LEFT JOIN validation_configs vc ON vr.config_id = vc.id
        LEFT JOIN datasets d            ON vc.dataset_id = d.id
        ORDER BY a.created_at DESC
        LIMIT :limit
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"limit": limit})
    for col in ("acknowledged_at", "sent_at", "created_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def acknowledge_alert(alert_id: int, by: str = "dashboard") -> None:
    with get_db_session() as session:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if alert is not None:
            alert.acknowledged = True
            alert.acknowledged_by = by
            alert.acknowledged_at = datetime.utcnow()
    clear_cache()


# ── Data Profiles (Step 3's output — not surfaced anywhere until now) ───────

@st.cache_data(ttl=15, show_spinner=False)
def get_latest_profile(dataset_id: int):
    """Returns (profile_row: dict | None, columns: dict). columns is the
    parsed `profile_json["columns"]` dict keyed by column name."""
    query = """
        SELECT id, dataset_id, row_count, column_count, profile_json, profiled_at
        FROM data_profiles
        WHERE dataset_id = :dataset_id
        ORDER BY profiled_at DESC
        LIMIT 1
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"dataset_id": dataset_id})
    if df.empty:
        return None, {}
    row = df.iloc[0].to_dict()
    try:
        parsed = json.loads(row["profile_json"])
    except (TypeError, ValueError):
        parsed = {}
    return row, parsed.get("columns", {})


@st.cache_data(ttl=15, show_spinner=False)
def get_profile_history(dataset_id: int, limit: int = 50) -> pd.DataFrame:
    query = """
        SELECT id, row_count, column_count, profiled_at
        FROM data_profiles
        WHERE dataset_id = :dataset_id
        ORDER BY profiled_at ASC
        LIMIT :limit
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"dataset_id": dataset_id, "limit": limit})
    if not df.empty:
        df["profiled_at"] = pd.to_datetime(df["profiled_at"])
    return df


# ── System status (for the sidebar) ──────────────────────────────────────────

@st.cache_data(ttl=5, show_spinner=False)
def check_db_alive() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
