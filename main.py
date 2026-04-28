"""
Responsibilities:
  • Session state management
  • Rendering indicators, controls, charts, news feed
  • Delegating ALL game logic to engine.py
  • Delegating ALL chart construction to charts.py
"""

import streamlit as st
import time

from engine import (
    COUNTRIES,
    GameState,
    new_game,
    step,
    final_score,
)
from charts import (
    dashboard_chart,
    gdp_growth_chart,
    inflation_chart,
    interest_rate_chart,
    debt_chart,
    fx_chart,
    reputation_chart,
    unemployment_chart,
    PALETTE,
)

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Global Macro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS — Finance Terminal aesthetic
# ─────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Space+Grotesk:wght@400;600;700&display=swap');

    /* Global reset */
    html, body, [class*="css"] {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #0a0e1a !important;
        color: #c8d8f0 !important;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Main container */
    .main .block-container {
        padding: 1rem 2rem 2rem 2rem;
        max-width: 100%;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0c1221 !important;
        border-right: 1px solid #1e2d4a;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {
        color: #c8d8f0 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Sliders */
    [data-testid="stSlider"] > div > div > div {
        background-color: #1e2d4a !important;
    }
    [data-testid="stSlider"] > div > div > div > div {
        background-color: #00e5ff !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0f3460 0%, #162040 100%) !important;
        color: #00e5ff !important;
        border: 1px solid #00e5ff !important;
        border-radius: 4px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.4rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #00e5ff22 0%, #0f346088 100%) !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.3) !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #0f1629 !important;
        border: 1px solid #1e2d4a !important;
        border-radius: 6px !important;
        padding: 0.75rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.65rem !important;
        letter-spacing: 0.1em !important;
        color: #4a6080 !important;
        text-transform: uppercase !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #c8d8f0 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }

    /* Progress bars */
    .stProgress > div > div > div {
        background-color: #1e2d4a !important;
    }

    /* Expander */
    [data-testid="stExpander"] {
        background-color: #0f1629 !important;
        border: 1px solid #1e2d4a !important;
        border-radius: 6px !important;
    }

    /* Selectbox */
    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #0f1629 !important;
        border-color: #1e2d4a !important;
    }

    /* Tabs */
    [data-testid="stTabs"] [role="tablist"] {
        gap: 0.5rem;
        border-bottom: 1px solid #1e2d4a;
    }
    [data-testid="stTabs"] [role="tab"] {
        background-color: #0f1629 !important;
        border: 1px solid #1e2d4a !important;
        border-radius: 4px 4px 0 0 !important;
        color: #4a6080 !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: #00e5ff !important;
        border-bottom-color: #0a0e1a !important;
    }

    /* Custom header */
    .gm-header {
        background: linear-gradient(90deg, #0c1221 0%, #0f1a35 50%, #0c1221 100%);
        border-bottom: 1px solid #1e2d4a;
        padding: 1rem 2rem;
        margin: -1rem -2rem 1.5rem -2rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .gm-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00e5ff;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
        text-shadow: 0 0 20px rgba(0,229,255,0.4);
    }
    .gm-subtitle {
        font-size: 0.7rem;
        color: #4a6080;
        letter-spacing: 0.2em;
        text-transform: uppercase;
    }

    /* KPI cards */
    .kpi-card {
        background: #0f1629;
        border: 1px solid #1e2d4a;
        border-radius: 6px;
        padding: 0.9rem 1rem;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
        background: var(--accent);
    }
    .kpi-label {
        font-size: 0.6rem;
        color: #4a6080;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--accent);
        font-family: 'JetBrains Mono', monospace;
    }
    .kpi-delta {
        font-size: 0.7rem;
        color: #4a6080;
        margin-top: 0.15rem;
    }

    /* News feed */
    .news-item {
        padding: 0.6rem 0.8rem;
        border-left: 3px solid #1e2d4a;
        margin-bottom: 0.5rem;
        background: #0f1629;
        border-radius: 0 4px 4px 0;
    }
    .news-item.negative { border-left-color: #ff4d6d; }
    .news-item.positive { border-left-color: #00e5ff; }
    .news-item.neutral  { border-left-color: #ffd166; }
    .news-day {
        font-size: 0.6rem;
        color: #4a6080;
        letter-spacing: 0.1em;
    }
    .news-headline {
        font-size: 0.78rem;
        color: #c8d8f0;
    }

    /* Reputation bar */
    .rep-bar-container {
        background: #1e2d4a;
        border-radius: 4px;
        height: 10px;
        width: 100%;
        overflow: hidden;
    }
    .rep-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }

    /* Day progress */
    .day-progress {
        background: #1e2d4a;
        border-radius: 2px;
        height: 4px;
        width: 100%;
        overflow: hidden;
        margin-top: 0.3rem;
    }
    .day-fill {
        height: 100%;
        background: linear-gradient(90deg, #00e5ff, #bd93f9);
        border-radius: 2px;
    }

    /* Country selector cards */
    .country-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0;
    }

    /* Alert box */
    .alert-box {
        border: 1px solid;
        border-radius: 6px;
        padding: 1rem 1.5rem;
        margin: 0.75rem 0;
        font-family: 'JetBrains Mono', monospace;
    }
    .alert-danger {
        border-color: #ff4d6d;
        background: rgba(255, 77, 109, 0.08);
        color: #ff4d6d;
    }
    .alert-success {
        border-color: #00e5ff;
        background: rgba(0, 229, 255, 0.06);
        color: #00e5ff;
    }
    .alert-warning {
        border-color: #ffd166;
        background: rgba(255, 209, 102, 0.06);
        color: #ffd166;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Session state helpers
# ─────────────────────────────────────────────

def _init_state() -> None:
    if "gs" not in st.session_state:
        st.session_state.gs = None
    if "screen" not in st.session_state:
        st.session_state.screen = "home"
    if "auto_play" not in st.session_state:
        st.session_state.auto_play = False
    if "speed" not in st.session_state:
        st.session_state.speed = 30  # days per step


def _start_game(country: str) -> None:
    st.session_state.gs = new_game(country)
    st.session_state.screen = "game"
    st.session_state.auto_play = False


def _reset() -> None:
    st.session_state.gs = None
    st.session_state.screen = "home"
    st.session_state.auto_play = False


# ─────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────

def _color_for_value(val: float, good_low: bool = False) -> str:
    """Return a hex colour based on whether a metric is good or bad."""
    if good_low:
        if val < 5:  return "#00e5ff"
        if val < 8:  return "#ffd166"
        return "#ff4d6d"
    else:
        if val > 0:  return "#00e5ff"
        if val > -1: return "#ffd166"
        return "#ff4d6d"


def _kpi(label: str, value: str, accent: str, delta: str = "") -> str:
    return f"""
    <div class="kpi-card" style="--accent:{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {'<div class="kpi-delta">' + delta + '</div>' if delta else ''}
    </div>"""


def _reputation_bar(rep: float) -> str:
    color = "#00e5ff" if rep > 50 else "#ffd166" if rep > 25 else "#ff4d6d"
    return f"""
    <div style="margin-bottom:0.25rem;font-size:0.6rem;letter-spacing:0.15em;color:#4a6080;text-transform:uppercase;">
        REPUTATION — {rep:.1f}%
    </div>
    <div class="rep-bar-container">
        <div class="rep-bar-fill" style="width:{rep}%;background:{color};"></div>
    </div>"""


def _day_progress(day: int, max_days: int) -> str:
    pct = day / max_days * 100
    return f"""
    <div style="margin-top:0.75rem;font-size:0.6rem;letter-spacing:0.1em;color:#4a6080;">
        DAY {day} / {max_days} — {pct:.1f}% TERM COMPLETE
    </div>
    <div class="day-progress">
        <div class="day-fill" style="width:{pct}%;"></div>
    </div>"""


def _render_news(gs: GameState) -> None:
    if not gs.news:
        st.markdown('<div style="color:#4a6080;font-size:0.75rem;">No events yet.</div>', unsafe_allow_html=True)
        return
    for item in gs.news[:12]:
        css_class = "positive" if item.impact > 0 else "negative" if item.impact < 0 else "neutral"
        st.markdown(f"""
        <div class="news-item {css_class}">
            <div class="news-day">DAY {item.day} · {item.category.upper()}</div>
            <div class="news-headline">{item.headline}</div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Home / country selection screen
# ─────────────────────────────────────────────

def render_home() -> None:
    st.markdown("""
    <div class="gm-header">
        <div>
            <div class="gm-title">⬡ GLOBAL MACRO</div>
            <div class="gm-subtitle">Central Bank Governor Simulation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="max-width:700px;margin:2rem auto 1.5rem;text-align:center;">
        <p style="font-size:1rem;color:#c8d8f0;line-height:1.7;">
            Step into the role of <span style="color:#00e5ff;font-weight:600;">Central Bank Governor</span> and 
            <span style="color:#bd93f9;font-weight:600;">Economic Planner</span> for a major world economy.
            Your mandate: survive a <span style="color:#ffd166;">1,200-day term</span> without crashing the economy 
            or being ousted by a political coup.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Quick-start guide
    with st.expander("📋  HOW TO PLAY", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
**🎯 OBJECTIVE**
- Survive the full 1,200-day term  
- Keep Reputation above 0%
- Maintain GDP Growth > 1.5%  
- Keep Inflation near 2–3%  
- Avoid Debt spiral (>150% GDP)

**⚠️ GAME OVER CONDITIONS**
- Reputation hits 0%
- Inflation exceeds 20%
- GDP Growth below −8% (depression)
- Debt/GDP exceeds 250%
            """)
        with c2:
            st.markdown("""
**🕹️ CONTROLS**
- **Rate Override** — adjust vs Taylor Rule; raise to fight inflation, cut to boost growth
- **Fiscal Balance** — surplus pays debt; deficit stimulates growth
- **QE / QT** — asset purchases lower spreads; sales cool bubbles
- **Tariffs** — trade protection; raises inflation, drags long-run growth

**📊 KEY TARGETS**
- Inflation: 2–3% ✅  
- GDP Growth: > 2% ✅  
- Debt / GDP: < 100% ✅  
- Unemployment: < 6% ✅
            """)

    st.markdown('<div style="text-align:center;margin:2rem 0 1rem;font-size:0.7rem;color:#4a6080;letter-spacing:0.2em;text-transform:uppercase;">— SELECT YOUR COUNTRY —</div>', unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (name, data) in enumerate(COUNTRIES.items()):
        with cols[i % 4]:
            preset = COUNTRIES[name]
            st.markdown(f"""
            <div style="background:#0f1629;border:1px solid #1e2d4a;border-radius:8px;padding:1rem;text-align:center;margin-bottom:0.5rem;">
                <div style="font-size:2rem;margin-bottom:0.3rem;">{data['flag']}</div>
                <div style="font-size:0.75rem;font-weight:600;color:#c8d8f0;margin-bottom:0.5rem;">{name}</div>
                <div style="font-size:0.65rem;color:#4a6080;">
                    GDP Growth: <span style="color:#00e5ff;">{preset['gdp_growth']}%</span><br>
                    Inflation: <span style="color:#ff4d6d;">{preset['inflation']}%</span><br>
                    Rate: <span style="color:#ffd166;">{preset['interest_rate']}%</span><br>
                    Debt/GDP: <span style="color:#ff9900;">{preset['debt_gdp']}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"▶  Play as {name.split()[0]}", key=f"start_{name}", use_container_width=True):
                _start_game(name)
                st.rerun()


# ─────────────────────────────────────────────
# Game screen
# ─────────────────────────────────────────────

def render_sidebar(gs: GameState) -> dict:
    """Render the control panel sidebar. Returns the player's chosen inputs."""
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:0.5rem 0 1rem;">
            <div style="font-size:2rem;">{gs.flag}</div>
            <div style="font-size:0.9rem;font-weight:700;color:#00e5ff;letter-spacing:0.1em;">{gs.country_name.upper()}</div>
            <div style="font-size:0.65rem;color:#4a6080;">GOVERNOR'S COMMAND CENTER</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Reputation & day
        st.markdown(_reputation_bar(gs.reputation), unsafe_allow_html=True)
        st.markdown(_day_progress(gs.day, gs.max_days), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div style="font-size:0.65rem;color:#4a6080;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.75rem;">◆ MONETARY POLICY</div>', unsafe_allow_html=True)

        rate_override = st.slider(
            "Rate Override (pp vs Taylor Rule)",
            min_value=-5.0, max_value=5.0,
            value=float(gs.rate_override), step=0.25,
            help="Positive = tighter than Taylor Rule. Negative = looser.",
        )
        qe_qt = st.slider(
            "QE / QT (% GDP)",
            min_value=-3.0, max_value=3.0,
            value=float(gs.qe_qt), step=0.25,
            help="Positive = asset purchases (QE). Negative = asset sales (QT).",
        )

        st.markdown('<div style="font-size:0.65rem;color:#4a6080;letter-spacing:0.15em;text-transform:uppercase;margin:0.75rem 0;">◆ FISCAL POLICY</div>', unsafe_allow_html=True)

        fiscal_balance = st.slider(
            "Primary Balance (% GDP)",
            min_value=-8.0, max_value=8.0,
            value=float(gs.fiscal_balance), step=0.5,
            help="Negative = deficit (stimulative). Positive = surplus (contractionary).",
        )

        st.markdown('<div style="font-size:0.65rem;color:#4a6080;letter-spacing:0.15em;text-transform:uppercase;margin:0.75rem 0;">◆ TRADE POLICY</div>', unsafe_allow_html=True)

        tariff_rate = st.slider(
            "Tariff Rate (%)",
            min_value=0.0, max_value=50.0,
            value=float(gs.tariff_rate), step=1.0,
            help="Higher tariffs boost short-term trade balance but hurt long-run growth.",
        )

        st.markdown("---")

        # Advance controls
        st.markdown('<div style="font-size:0.65rem;color:#4a6080;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:0.5rem;">◆ ADVANCE SIMULATION</div>', unsafe_allow_html=True)

        speed = st.select_slider(
            "Step Size",
            options=[7, 14, 30, 60, 90],
            value=st.session_state.speed,
            format_func=lambda x: f"{x} days",
        )
        st.session_state.speed = speed

        col_a, col_b = st.columns(2)
        with col_a:
            advance = st.button("▶  ADVANCE", use_container_width=True)
        with col_b:
            auto_toggle = st.button(
                "⏸  PAUSE" if st.session_state.auto_play else "⏩  AUTO",
                use_container_width=True,
            )

        if auto_toggle:
            st.session_state.auto_play = not st.session_state.auto_play

        st.markdown("---")
        if st.button("↩  RESTART", use_container_width=True):
            _reset()
            st.rerun()

    return {
        "rate_override": rate_override,
        "qe_qt": qe_qt,
        "fiscal_balance": fiscal_balance,
        "tariff_rate": tariff_rate,
        "advance": advance,
    }


def _delta_arrow(current: float, history: list[float]) -> str:
    if len(history) < 2:
        return "—"
    prev = history[-2]
    diff = current - prev
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "—"
    return f"{arrow} {abs(diff):.2f}"


def render_game(gs: GameState) -> None:
    """Main game screen."""
    # Header
    pct_done = gs.day / gs.max_days * 100
    st.markdown(f"""
    <div class="gm-header">
        <div style="flex:1;">
            <div class="gm-title">⬡ GLOBAL MACRO</div>
            <div class="gm-subtitle">{gs.flag} {gs.country_name} · {gs.currency} · Day {gs.day} / {gs.max_days}</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.65rem;color:#4a6080;letter-spacing:0.12em;text-transform:uppercase;">Term Progress</div>
            <div style="font-size:1.2rem;font-weight:700;color:#bd93f9;">{pct_done:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Active shock banner
    if gs.last_shock:
        st.markdown(f'<div class="alert-box alert-warning">⚡ MARKET EVENT: {gs.last_shock.upper()}</div>', unsafe_allow_html=True)

    # ── KPI strip ──────────────────────────────────────────────────────
    cols = st.columns(8)

    kpi_data = [
        ("GDP Growth", f"{gs.gdp_growth:+.2f}%", PALETTE["gdp"],
         _delta_arrow(gs.gdp_growth, gs.history_gdp_growth)),
        ("Inflation", f"{gs.inflation:.2f}%", PALETTE["inflation"],
         _delta_arrow(gs.inflation, gs.history_inflation)),
        ("Policy Rate", f"{gs.interest_rate:.2f}%", PALETTE["rate"],
         _delta_arrow(gs.interest_rate, gs.history_interest_rate)),
        ("Debt / GDP", f"{gs.debt_gdp:.1f}%", PALETTE["debt"],
         _delta_arrow(gs.debt_gdp, gs.history_debt_gdp)),
        ("FX vs USD", f"{gs.fx:.3f}", PALETTE["fx"],
         _delta_arrow(gs.fx, gs.history_fx)),
        ("Unemployment", f"{gs.unemployment:.1f}%", PALETTE["unemployment"],
         _delta_arrow(gs.unemployment, gs.history_unemployment)),
        ("Global Risk χ", f"{gs.global_risk:.2f}", "#ff9900",
         ""),
        ("Reputation", f"{gs.reputation:.1f}%", PALETTE["reputation"],
         _delta_arrow(gs.reputation, gs.history_reputation)),
    ]

    for col, (label, value, accent, delta) in zip(cols, kpi_data):
        with col:
            st.markdown(_kpi(label, value, accent, delta), unsafe_allow_html=True)

    st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────
    tab_overview, tab_charts, tab_news = st.tabs(
        ["📊  DASHBOARD", "📈  DETAILED CHARTS", "📰  NEWS FEED"]
    )

    with tab_overview:
        st.plotly_chart(dashboard_chart(gs), use_container_width=True, config={"displayModeBar": False})

        # Warnings
        warnings = []
        if gs.inflation > 6:    warnings.append(("danger", f"⚠ INFLATION CRISIS: {gs.inflation:.1f}% — far above 2% target. Raise rates urgently."))
        if gs.inflation < 0:    warnings.append(("danger", f"⚠ DEFLATION RISK: {gs.inflation:.1f}% — cut rates and stimulate."))
        if gs.gdp_growth < 0:   warnings.append(("danger", f"⚠ RECESSION: Growth at {gs.gdp_growth:.1f}%."))
        if gs.debt_gdp > 130:   warnings.append(("warning", f"⚠ DEBT ALARM: {gs.debt_gdp:.0f}% — markets watching closely."))
        if gs.unemployment > 9: warnings.append(("warning", f"⚠ HIGH UNEMPLOYMENT: {gs.unemployment:.1f}%"))
        if gs.reputation < 25:  warnings.append(("danger", f"⚠ REPUTATION CRITICAL: {gs.reputation:.1f}% — at risk of removal."))

        for kind, msg in warnings:
            st.markdown(f'<div class="alert-box alert-{kind}">{msg}</div>', unsafe_allow_html=True)

        if not warnings:
            st.markdown('<div class="alert-box alert-success">✔ ALL INDICATORS WITHIN ACCEPTABLE RANGE</div>', unsafe_allow_html=True)

    with tab_charts:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.plotly_chart(gdp_growth_chart(gs), use_container_width=True, config={"displayModeBar": False})
            st.plotly_chart(interest_rate_chart(gs), use_container_width=True, config={"displayModeBar": False})
            st.plotly_chart(unemployment_chart(gs), use_container_width=True, config={"displayModeBar": False})
        with r1c2:
            st.plotly_chart(inflation_chart(gs), use_container_width=True, config={"displayModeBar": False})
            st.plotly_chart(debt_chart(gs), use_container_width=True, config={"displayModeBar": False})
            st.plotly_chart(fx_chart(gs), use_container_width=True, config={"displayModeBar": False})

    with tab_news:
        st.markdown('<div style="font-size:0.65rem;color:#4a6080;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:1rem;">— LIVE MARKET INTELLIGENCE FEED —</div>', unsafe_allow_html=True)
        _render_news(gs)


# ─────────────────────────────────────────────
# End screen
# ─────────────────────────────────────────────

def render_end(gs: GameState) -> None:
    score = final_score(gs)

    grade_colors = {"S": "#00e5ff", "A": "#a8ff78", "B": "#ffd166", "C": "#ff9900", "D": "#ff79c6", "F": "#ff4d6d"}
    gc = grade_colors.get(score.get("grade", "F"), "#c8d8f0")

    st.markdown(f"""
    <div style="text-align:center;padding:3rem 0 2rem;">
        <div style="font-size:0.7rem;color:#4a6080;letter-spacing:0.3em;text-transform:uppercase;margin-bottom:1rem;">
            {'— TERM COMPLETE —' if gs.game_won else '— MANDATE ENDED —'}
        </div>
        <div style="font-size:4rem;margin-bottom:0.5rem;">{'🏆' if gs.game_won else '📉'}</div>
        <div style="font-size:1.1rem;color:#c8d8f0;max-width:500px;margin:0 auto 2rem;">{gs.end_reason}</div>
        <div style="font-size:6rem;font-weight:700;color:{gc};line-height:1;text-shadow:0 0 40px {gc}88;">
            {score.get('grade','?')}
        </div>
        <div style="font-size:1rem;color:#4a6080;margin-top:0.25rem;">
            FINAL SCORE: {score.get('total',0):.1f} / 100
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Score breakdown
    c1, c2, c3, c4 = st.columns(4)
    breakdown = [
        (c1, "Growth Score", score.get("growth_score", 0), 40, PALETTE["gdp"]),
        (c2, "Inflation Score", score.get("inflation_score", 0), 30, PALETTE["inflation"]),
        (c3, "Debt Score", score.get("debt_score", 0), 20, PALETTE["debt"]),
        (c4, "Survival Score", score.get("survival_score", 0), 10, PALETTE["reputation"]),
    ]
    for col, label, val, mx, color in breakdown:
        with col:
            st.markdown(_kpi(label, f"{val:.1f}/{mx}", color), unsafe_allow_html=True)

    st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)

    # Stats row
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (c1, "Avg GDP Growth", f"{score.get('avg_growth',0):.2f}%", PALETTE["gdp"]),
        (c2, "Avg Inflation", f"{score.get('avg_inflation',0):.2f}%", PALETTE["inflation"]),
        (c3, "Avg Debt/GDP", f"{score.get('avg_debt',0):.1f}%", PALETTE["debt"]),
        (c4, "Days Survived", str(score.get('days_survived', 0)), PALETTE["reputation"]),
    ]
    for col, label, val, color in stats:
        with col:
            st.markdown(_kpi(label, val, color), unsafe_allow_html=True)

    st.markdown("<div style='margin:2rem 0'></div>", unsafe_allow_html=True)
    col_a, col_b, _ = st.columns([1, 1, 2])
    with col_a:
        if st.button("▶  PLAY AGAIN", use_container_width=True):
            _start_game(gs.country_name)
            st.rerun()
    with col_b:
        if st.button("↩  MAIN MENU", use_container_width=True):
            _reset()
            st.rerun()


# ─────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────

def main() -> None:
    _init_state()
    gs: GameState = st.session_state.gs

    if st.session_state.screen == "home" or gs is None:
        render_home()
        return

    # ── Sidebar controls ──
    controls = render_sidebar(gs)

    # Apply control inputs to state
    gs.rate_override = controls["rate_override"]
    gs.qe_qt = controls["qe_qt"]
    gs.fiscal_balance = controls["fiscal_balance"]
    gs.tariff_rate = controls["tariff_rate"]

    # ── Game over? ──
    if gs.game_over:
        render_end(gs)
        return

    # ── Advance simulation ──
    should_advance = controls["advance"] or st.session_state.auto_play
    if should_advance:
        step(gs, days=st.session_state.speed)
        st.session_state.gs = gs
        if st.session_state.auto_play and not gs.game_over:
            time.sleep(0.4)
        st.rerun()

    # ── Render game ──
    render_game(gs)


if __name__ == "__main__":
    main()
