"""
charts.py — Plotly chart builders for Global Macro.

Each function accepts a GameState and returns a plotly Figure.
Zero Streamlit imports.
"""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from engine import GameState

# ---------------------------------------------------------------------------
# Design tokens – "Finance Terminal" aesthetic
# ---------------------------------------------------------------------------

DARK_BG = "#0a0e1a"
PANEL_BG = "#0f1629"
GRID_COLOR = "#1e2d4a"
TEXT_COLOR = "#c8d8f0"
MUTED_TEXT = "#4a6080"

PALETTE = {
    "gdp":        "#00e5ff",   # cyan
    "inflation":  "#ff4d6d",   # coral-red
    "rate":       "#ffd166",   # amber
    "debt":       "#ff9900",   # orange
    "fx":         "#a8ff78",   # lime
    "reputation": "#bd93f9",   # lavender
    "unemployment": "#ff79c6", # pink
}

CHART_DEFAULTS = dict(
    paper_bgcolor=DARK_BG,
    plot_bgcolor=PANEL_BG,
    font=dict(family="JetBrains Mono, monospace", color=TEXT_COLOR, size=11),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False),
    yaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False),
)


def _base_line(name: str, x, y, color: str, dash="solid") -> go.Scatter:
    return go.Scatter(
        x=x, y=y, name=name,
        line=dict(color=color, width=2, dash=dash),
        mode="lines",
        hovertemplate=f"<b>{name}</b><br>Day %{{x}}<br>%{{y:.2f}}<extra></extra>",
    )


# ---------------------------------------------------------------------------
# Individual charts
# ---------------------------------------------------------------------------

def gdp_growth_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(_base_line("GDP Growth %", gs.history_days, gs.history_gdp_growth, PALETTE["gdp"]))
    fig.add_hline(y=0, line=dict(color="#ff4d6d", dash="dash", width=1))
    fig.add_hline(y=2, line=dict(color=MUTED_TEXT, dash="dot", width=1))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="GDP GROWTH RATE (%)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        showlegend=False,
    )
    return fig


def inflation_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_hrect(y0=1.5, y1=3.5, fillcolor="rgba(0,229,255,0.04)", line_width=0)
    fig.add_trace(_base_line("Inflation %", gs.history_days, gs.history_inflation, PALETTE["inflation"]))
    fig.add_hline(y=2.0, line=dict(color="#00e5ff", dash="dot", width=1))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="INFLATION (%)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        showlegend=False,
    )
    return fig


def interest_rate_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(_base_line("Policy Rate %", gs.history_days, gs.history_interest_rate, PALETTE["rate"]))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="POLICY INTEREST RATE (%)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        showlegend=False,
    )
    return fig


def debt_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_hline(y=100, line=dict(color="#ffd166", dash="dash", width=1))
    fig.add_trace(_base_line("Debt / GDP %", gs.history_days, gs.history_debt_gdp, PALETTE["debt"]))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="DEBT / GDP (%)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        showlegend=False,
    )
    return fig


def fx_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(_base_line(f"FX vs USD", gs.history_days, gs.history_fx, PALETTE["fx"]))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="FX RATE (vs USD)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        showlegend=False,
    )
    return fig


def reputation_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=25, fillcolor="rgba(255,77,109,0.08)", line_width=0)
    fig.add_trace(go.Scatter(
        x=gs.history_days, y=gs.history_reputation,
        name="Reputation",
        fill="tozeroy",
        fillcolor="rgba(189,147,249,0.15)",
        line=dict(color=PALETTE["reputation"], width=2),
        mode="lines",
        hovertemplate="<b>Reputation</b><br>Day %{x}<br>%{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=25, line=dict(color="#ff4d6d", dash="dash", width=1))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="GOVERNOR REPUTATION (%)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        yaxis=dict(gridcolor=GRID_COLOR, range=[0, 100]),
        showlegend=False,
    )
    return fig


def dashboard_chart(gs: GameState) -> go.Figure:
    """4-panel overview chart."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("GDP Growth %", "Inflation %", "Debt / GDP %", "Reputation %"),
        vertical_spacing=0.18,
        horizontal_spacing=0.12,
    )

    fig.add_trace(go.Scatter(x=gs.history_days, y=gs.history_gdp_growth,
                             line=dict(color=PALETTE["gdp"], width=2), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=gs.history_days, y=gs.history_inflation,
                             line=dict(color=PALETTE["inflation"], width=2), showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=gs.history_days, y=gs.history_debt_gdp,
                             line=dict(color=PALETTE["debt"], width=2), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=gs.history_days, y=gs.history_reputation,
                             fill="tozeroy", fillcolor="rgba(189,147,249,0.12)",
                             line=dict(color=PALETTE["reputation"], width=2), showlegend=False), row=2, col=2)

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=PANEL_BG,
        font=dict(family="JetBrains Mono, monospace", color=TEXT_COLOR, size=10),
        margin=dict(l=50, r=20, t=50, b=40),
        height=420,
    )
    for i in fig['layout']['annotations']:
        i['font'] = dict(color=MUTED_TEXT, size=11)
    for axis in fig.layout:
        if 'xaxis' in axis or 'yaxis' in axis:
            fig.layout[axis].update(gridcolor=GRID_COLOR, showgrid=True, zeroline=False)

    return fig


def unemployment_chart(gs: GameState) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(_base_line("Unemployment %", gs.history_days, gs.history_unemployment, PALETTE["unemployment"]))
    fig.update_layout(
        **CHART_DEFAULTS,
        title=dict(text="UNEMPLOYMENT (%)", font=dict(size=12, color=MUTED_TEXT)),
        height=220,
        showlegend=False,
    )
    return fig
