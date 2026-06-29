"""
src/dashboard/style.py
=======================
Shared visual language for every page of the DataNexus dashboard:
custom CSS injection, status/severity color maps, and a reusable
page-header component so every page looks like part of one product
instead of five separate Streamlit scripts.
"""

import streamlit as st

# ── Brand palette ──────────────────────────────────────────────────────────
ACCENT      = "#22D3EE"   # cyan — primary brand accent
ACCENT_SOFT = "#0E7490"
BG_CARD     = "#121821"
BG_CARD_2   = "#161D27"
BORDER      = "#202733"

PASS_COLOR    = "#34D399"
FAIL_COLOR    = "#F87171"
ERROR_COLOR   = "#FBBF24"
SKIP_COLOR    = "#94A3B8"
PENDING_COLOR = "#64748B"
RUNNING_COLOR = "#60A5FA"

STATUS_COLORS = {
    "pass":    PASS_COLOR,
    "fail":    FAIL_COLOR,
    "error":   ERROR_COLOR,
    "skip":    SKIP_COLOR,
    "pending": PENDING_COLOR,
    "running": RUNNING_COLOR,
}

STATUS_EMOJI = {
    "pass":    "✅",
    "fail":    "❌",
    "error":   "⚠️",
    "skip":    "⏭️",
    "pending": "🕓",
    "running": "🔄",
}

SEVERITY_COLORS = {
    "critical": "#F87171",
    "high":     "#FB923C",
    "medium":   "#FBBF24",
    "low":      "#94A3B8",
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "⚪",
}


def score_color(score: float) -> str:
    """Map a 0-100 quality score to a traffic-light color."""
    if score is None:
        return PENDING_COLOR
    if score >= 90:
        return PASS_COLOR
    if score >= 70:
        return "#A3E635"
    if score >= 50:
        return ERROR_COLOR
    return FAIL_COLOR


def inject_theme() -> None:
    """Inject shared CSS. Call once near the top of every page."""
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

            html, body, [class*="css"] {{
                font-family: 'Inter', sans-serif;
            }}

            /* Tighten default Streamlit top padding */
            .block-container {{
                padding-top: 2rem;
                padding-bottom: 3rem;
            }}

            /* ── KPI / metric cards ───────────────────────────────────── */
            div[data-testid="stMetric"] {{
                background: linear-gradient(145deg, {BG_CARD} 0%, {BG_CARD_2} 100%);
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 14px 18px 10px 18px;
                box-shadow: 0 4px 18px rgba(0,0,0,0.25);
            }}
            div[data-testid="stMetricValue"] {{
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
            }}
            div[data-testid="stMetricLabel"] {{
                color: #9CA3AF;
                font-size: 0.8rem;
                letter-spacing: 0.03em;
                text-transform: uppercase;
            }}

            /* ── Header banner ────────────────────────────────────────── */
            .dn-header {{
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 18px 22px;
                margin-bottom: 18px;
                border-radius: 16px;
                background: linear-gradient(120deg, rgba(34,211,238,0.12) 0%, rgba(11,15,20,0.0) 70%);
                border: 1px solid {BORDER};
            }}
            .dn-header-icon {{
                font-size: 2.1rem;
                line-height: 1;
            }}
            .dn-header-title {{
                font-size: 1.55rem;
                font-weight: 700;
                color: #F3F4F6;
                margin: 0;
            }}
            .dn-header-subtitle {{
                color: #9CA3AF;
                font-size: 0.92rem;
                margin: 2px 0 0 0;
            }}

            /* ── Status / severity pills ──────────────────────────────── */
            .dn-pill {{
                display: inline-block;
                padding: 2px 10px;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 600;
                font-family: 'JetBrains Mono', monospace;
                white-space: nowrap;
            }}

            /* ── Section caption ──────────────────────────────────────── */
            .dn-section {{
                color: {ACCENT};
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin: 6px 0 2px 0;
                border-bottom: 1px solid {BORDER};
                padding-bottom: 6px;
            }}

            .dn-empty {{
                text-align: center;
                padding: 50px 20px;
                color: #9CA3AF;
                border: 1px dashed {BORDER};
                border-radius: 14px;
                background: {BG_CARD};
            }}

            /* ── Plain HTML tables (used where pills/badges need raw HTML) ── */
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.88rem;
            }}
            table thead th {{
                text-align: left;
                color: #9CA3AF;
                font-size: 0.74rem;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                border-bottom: 1px solid {BORDER};
                padding: 8px 10px;
            }}
            table tbody td {{
                padding: 9px 10px;
                border-bottom: 1px solid {BORDER};
                color: #E5E7EB;
            }}
            table tbody tr:hover {{
                background: rgba(34,211,238,0.05);
            }}

            section[data-testid="stSidebar"] {{
                border-right: 1px solid {BORDER};
            }}

            /* ── Sidebar nav link polish (best-effort: Streamlit's internal
               testids for nav links have been stable across 1.3x–1.4x, but
               could shift in future releases — this degrades harmlessly
               to plain links if the selector ever stops matching) ──────── */
            section[data-testid="stSidebar"] a {{
                border-radius: 8px;
                transition: background 0.15s ease;
            }}
            section[data-testid="stSidebar"] a:hover {{
                background: rgba(34,211,238,0.08) !important;
            }}
            [data-testid="stSidebarNavLink"][aria-current="page"] {{
                background: rgba(34,211,238,0.14) !important;
                border-left: 3px solid {ACCENT};
            }}

            /* ── Sidebar brand block ──────────────────────────────────── */
            .dn-side-brand {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 4px 2px 14px 2px;
            }}
            .dn-side-brand .icon {{ font-size: 1.7rem; }}
            .dn-side-brand .title {{
                font-weight: 700;
                font-size: 1.05rem;
                color: #F3F4F6;
                margin: 0;
                line-height: 1.1;
            }}
            .dn-side-brand .subtitle {{
                color: #6B7280;
                font-size: 0.72rem;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                margin: 0;
            }}
            .dn-side-status {{
                display: flex;
                justify-content: space-between;
                font-size: 0.78rem;
                color: #9CA3AF;
                padding: 3px 2px;
            }}
            .dn-side-status .dot {{
                display: inline-block;
                width: 8px; height: 8px;
                border-radius: 50%;
                margin-right: 6px;
            }}
            .dn-side-divider {{
                border-top: 1px solid {BORDER};
                margin: 10px 0 12px 0;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    """Render the consistent page banner used at the top of every page."""
    st.markdown(
        f"""
        <div class="dn-header">
            <div class="dn-header-icon">{icon}</div>
            <div>
                <p class="dn-header-title">{title}</p>
                <p class="dn-header-subtitle">{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand(db_alive: bool, last_run_text: str, open_alerts: int) -> None:
    """Custom branding + live status block rendered above the nav menu."""
    st.markdown(
        """
        <div class="dn-side-brand">
            <div class="icon">🛰️</div>
            <div>
                <p class="title">DataNexus</p>
                <p class="subtitle">Data Quality Observatory</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dot_color = PASS_COLOR if db_alive else FAIL_COLOR
    db_text = "Connected" if db_alive else "Unreachable"
    st.markdown(
        f"""
        <div class="dn-side-status">
            <span><span class="dot" style="background:{dot_color};"></span>Database</span>
            <span>{db_text}</span>
        </div>
        <div class="dn-side-status">
            <span>Last run</span><span>{last_run_text}</span>
        </div>
        <div class="dn-side-status">
            <span>Open alerts</span>
            <span style="color:{FAIL_COLOR if open_alerts else '#9CA3AF'};">{open_alerts}</span>
        </div>
        <div class="dn-side-divider"></div>
        """,
        unsafe_allow_html=True,
    )


def section(label: str) -> None:
    st.markdown(f'<div class="dn-section">{label}</div>', unsafe_allow_html=True)


def status_pill_html(status: str) -> str:
    s = str(status).lower().strip()
    color = STATUS_COLORS.get(s, PENDING_COLOR)
    emoji = STATUS_EMOJI.get(s, "•")
    return (
        f'<span class="dn-pill" style="background:{color}22; color:{color}; '
        f'border:1px solid {color}55;">{emoji} {s.upper()}</span>'
    )


def severity_pill_html(severity: str) -> str:
    s = str(severity).lower().strip()
    color = SEVERITY_COLORS.get(s, SEVERITY_COLORS["low"])
    emoji = SEVERITY_EMOJI.get(s, "⚪")
    return (
        f'<span class="dn-pill" style="background:{color}22; color:{color}; '
        f'border:1px solid {color}55;">{emoji} {s.upper()}</span>'
    )


def empty_state(message: str) -> None:
    st.markdown(f'<div class="dn-empty">{message}</div>', unsafe_allow_html=True)
