"""
src/dashboard/components/score_gauge.py
=========================================
Plotly figure factories for the Quality Score visuals used across
the Overview and Run Details pages.
"""

import plotly.graph_objects as go

from src.dashboard.style import score_color


def render_score_gauge(score: float, title: str = "Quality Score", threshold: float = None) -> go.Figure:
    """A speedometer-style gauge for a single 0-100 quality score."""
    value = score if score is not None else 0
    color = score_color(score)

    steps = [
        {"range": [0, 50],  "color": "rgba(248,113,113,0.12)"},
        {"range": [50, 70], "color": "rgba(251,191,36,0.12)"},
        {"range": [70, 90], "color": "rgba(163,230,53,0.12)"},
        {"range": [90, 100], "color": "rgba(52,211,153,0.12)"},
    ]

    gauge = {
        "axis": {"range": [0, 100], "tickcolor": "#6B7280", "tickwidth": 1},
        "bar": {"color": color, "thickness": 0.28},
        "bgcolor": "rgba(0,0,0,0)",
        "borderwidth": 0,
        "steps": steps,
    }
    if threshold is not None:
        gauge["threshold"] = {
            "line": {"color": "#E5E7EB", "width": 3},
            "thickness": 0.85,
            "value": threshold,
        }

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "", "font": {"size": 38, "color": color}},
            title={"text": title, "font": {"size": 14, "color": "#9CA3AF"}},
            gauge=gauge,
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#E5E7EB"},
        height=240,
        margin=dict(l=24, r=24, t=46, b=10),
    )
    return fig


def render_mini_score(score: float) -> go.Figure:
    """A compact 'number only' indicator for tight table-adjacent layouts."""
    color = score_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="number",
            value=score if score is not None else 0,
            number={"suffix": "", "font": {"size": 28, "color": color}},
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=80,
        margin=dict(l=4, r=4, t=4, b=4),
    )
    return fig
