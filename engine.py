"""
engine.py — Global Macro simulation engine (v2).

Changes vs v1:
  - Active shock system: shocks persist for multiple steps (duration + decay)
  - Crisis cascade: bad indicators trigger secondary crises
  - Policy forecast: helper returns projected next-step values for UI preview
  - Confidence system: market confidence affects borrowing costs
  - Expanded shock catalogue with severity tiers
  - Contagion events: global risk can spike hard
  - Milestones / achievements tracked
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Country presets
# ---------------------------------------------------------------------------

COUNTRIES: dict[str, dict] = {
    "United States": {
        "flag": "🇺🇸",
        "currency": "USD",
        "gdp": 100.0,
        "gdp_growth": 2.5,
        "inflation": 2.1,
        "interest_rate": 5.25,
        "debt_gdp": 122.0,
        "fx": 1.00,
        "unemployment": 4.0,
        "trade_balance": -3.2,
        "productivity": 1.0,
        "base_growth": 2.5,
        "difficulty": "Medium",
    },
    "European Union": {
        "flag": "🇪🇺",
        "currency": "EUR",
        "gdp": 100.0,
        "gdp_growth": 1.8,
        "inflation": 2.4,
        "interest_rate": 4.50,
        "debt_gdp": 90.0,
        "fx": 1.08,
        "unemployment": 6.1,
        "trade_balance": 1.5,
        "productivity": 0.98,
        "base_growth": 1.8,
        "difficulty": "Medium",
    },
    "China": {
        "flag": "🇨🇳",
        "currency": "CNY",
        "gdp": 100.0,
        "gdp_growth": 5.2,
        "inflation": 0.3,
        "interest_rate": 3.45,
        "debt_gdp": 77.0,
        "fx": 7.24,
        "unemployment": 5.2,
        "trade_balance": 3.8,
        "productivity": 1.05,
        "base_growth": 5.2,
        "difficulty": "Hard",
    },
    "Japan": {
        "flag": "🇯🇵",
        "currency": "JPY",
        "gdp": 100.0,
        "gdp_growth": 1.2,
        "inflation": 2.8,
        "interest_rate": 0.10,
        "debt_gdp": 261.0,
        "fx": 148.0,
        "unemployment": 2.6,
        "trade_balance": -0.5,
        "productivity": 0.95,
        "base_growth": 1.2,
        "difficulty": "Very Hard",
    },
    "United Kingdom": {
        "flag": "🇬🇧",
        "currency": "GBP",
        "gdp": 100.0,
        "gdp_growth": 1.5,
        "inflation": 3.2,
        "interest_rate": 5.25,
        "debt_gdp": 101.0,
        "fx": 0.79,
        "unemployment": 4.2,
        "trade_balance": -3.5,
        "productivity": 0.96,
        "base_growth": 1.5,
        "difficulty": "Medium",
    },
    "Brazil": {
        "flag": "🇧🇷",
        "currency": "BRL",
        "gdp": 100.0,
        "gdp_growth": 3.1,
        "inflation": 4.6,
        "interest_rate": 10.50,
        "debt_gdp": 88.0,
        "fx": 5.05,
        "unemployment": 7.8,
        "trade_balance": 1.9,
        "productivity": 0.90,
        "base_growth": 3.1,
        "difficulty": "Hard",
    },
    "India": {
        "flag": "🇮🇳",
        "currency": "INR",
        "gdp": 100.0,
        "gdp_growth": 6.8,
        "inflation": 4.9,
        "interest_rate": 6.50,
        "debt_gdp": 82.0,
        "fx": 83.1,
        "unemployment": 8.1,
        "trade_balance": -2.1,
        "productivity": 1.08,
        "base_growth": 6.8,
        "difficulty": "Easy",
    },
}

# ---------------------------------------------------------------------------
# Shock catalogue — tiered severity
# ---------------------------------------------------------------------------

RANDOM_EVENTS: list[dict] = [
    # ── Minor (common) ──────────────────────────────────────────────────
    {"name": "Strong Jobs Report",        "tier": 1, "inflation_shock": 0.3,  "growth_shock": 0.4,  "fx_shock":  0.02, "probability": 0.06, "duration": 1, "rep_shock": 1.0},
    {"name": "Weak Earnings Season",      "tier": 1, "inflation_shock":-0.1,  "growth_shock":-0.4,  "fx_shock": -0.01, "probability": 0.05, "duration": 1, "rep_shock":-0.5},
    {"name": "Consumer Confidence Surge", "tier": 1, "inflation_shock": 0.2,  "growth_shock": 0.5,  "fx_shock":  0.01, "probability": 0.05, "duration": 1, "rep_shock": 0.8},
    {"name": "Housing Slowdown",          "tier": 1, "inflation_shock":-0.2,  "growth_shock":-0.3,  "fx_shock": -0.01, "probability": 0.04, "duration": 2, "rep_shock":-0.5},
    {"name": "Tech Sector Boom",          "tier": 1, "inflation_shock": 0.2,  "growth_shock": 0.8,  "fx_shock":  0.02, "probability": 0.04, "duration": 2, "rep_shock": 1.5},
    {"name": "Productivity Surge",        "tier": 1, "inflation_shock":-0.2,  "growth_shock": 0.7,  "fx_shock":  0.03, "probability": 0.03, "duration": 3, "rep_shock": 2.0},
    {"name": "Rating Agency Upgrade",     "tier": 1, "inflation_shock": 0.0,  "growth_shock": 0.2,  "fx_shock":  0.03, "probability": 0.02, "duration": 1, "rep_shock": 3.0},
    {"name": "Rating Agency Downgrade",   "tier": 1, "inflation_shock": 0.2,  "growth_shock":-0.3,  "fx_shock": -0.04, "probability": 0.02, "duration": 2, "rep_shock":-4.0},

    # ── Moderate ────────────────────────────────────────────────────────
    {"name": "Oil Price Spike",           "tier": 2, "inflation_shock": 0.8,  "growth_shock":-0.5,  "fx_shock": -0.02, "probability": 0.04, "duration": 3, "rep_shock":-1.5},
    {"name": "Oil Price Crash",           "tier": 2, "inflation_shock":-0.6,  "growth_shock": 0.3,  "fx_shock":  0.01, "probability": 0.03, "duration": 2, "rep_shock": 0.5},
    {"name": "Supply Chain Disruption",   "tier": 2, "inflation_shock": 1.0,  "growth_shock":-0.6,  "fx_shock": -0.01, "probability": 0.03, "duration": 4, "rep_shock":-2.0},
    {"name": "Commodity Supercycle",      "tier": 2, "inflation_shock": 0.9,  "growth_shock": 0.4,  "fx_shock":  0.01, "probability": 0.02, "duration": 4, "rep_shock":-1.0},
    {"name": "Debt Ceiling Crisis",       "tier": 2, "inflation_shock": 0.3,  "growth_shock":-0.5,  "fx_shock": -0.02, "probability": 0.02, "duration": 2, "rep_shock":-3.0},
    {"name": "Currency War Escalation",   "tier": 2, "inflation_shock": 0.4,  "growth_shock":-0.3,  "fx_shock": -0.05, "probability": 0.02, "duration": 3, "rep_shock":-2.0},
    {"name": "Geopolitical Shock",        "tier": 2, "inflation_shock": 0.6,  "growth_shock":-0.7,  "fx_shock": -0.03, "probability": 0.03, "duration": 3, "rep_shock":-2.5},

    # ── Severe ──────────────────────────────────────────────────────────
    {"name": "Banking Sector Stress",     "tier": 3, "inflation_shock": 0.1,  "growth_shock":-0.9,  "fx_shock": -0.04, "probability": 0.015,"duration": 5, "rep_shock":-5.0},
    {"name": "Capital Flight Episode",    "tier": 3, "inflation_shock": 0.5,  "growth_shock":-0.8,  "fx_shock": -0.06, "probability": 0.015,"duration": 4, "rep_shock":-4.0},
    {"name": "Global Recession Signal",   "tier": 3, "inflation_shock":-0.3,  "growth_shock":-1.2,  "fx_shock":  0.03, "probability": 0.02, "duration": 6, "rep_shock":-4.0},

    # ── Black Swan ──────────────────────────────────────────────────────
    {"name": "Financial Contagion",       "tier": 4, "inflation_shock": 1.5,  "growth_shock":-2.5,  "fx_shock": -0.10, "probability": 0.005,"duration": 8, "rep_shock":-8.0, "global_risk_shock": 0.25},
    {"name": "Pandemic Shock",            "tier": 4, "inflation_shock":-0.5,  "growth_shock":-4.0,  "fx_shock": -0.08, "probability": 0.003,"duration":10, "rep_shock":-6.0, "global_risk_shock": 0.30},
    {"name": "War & Sanctions",           "tier": 4, "inflation_shock": 2.5,  "growth_shock":-3.0,  "fx_shock": -0.12, "probability": 0.004,"duration": 9, "rep_shock":-7.0, "global_risk_shock": 0.20},
]

TIER_COLORS = {1: "🟡", 2: "🟠", 3: "🔴", 4: "☠️"}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ActiveShock:
    name: str
    tier: int
    steps_remaining: int
    inflation_shock: float
    growth_shock: float
    fx_shock: float
    rep_shock: float = 0.0
    global_risk_shock: float = 0.0


@dataclass
class NewsItem:
    day: int
    headline: str
    impact: float
    category: str   # "monetary" | "fiscal" | "trade" | "event" | "milestone" | "crisis"
    tier: int = 1   # 1-4 severity


@dataclass
class Milestone:
    day: int
    title: str
    description: str


# ---------------------------------------------------------------------------
# Core GameState
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    # Meta
    country_name: str = "United States"
    day: int = 0
    max_days: int = 1200
    game_over: bool = False
    game_won: bool = False
    end_reason: str = ""

    # Economic indicators
    gdp: float = 100.0
    gdp_growth: float = 2.5
    inflation: float = 2.1
    interest_rate: float = 5.25
    debt_gdp: float = 122.0
    fx: float = 1.00
    unemployment: float = 4.0
    trade_balance: float = -3.2
    productivity: float = 1.0
    base_growth: float = 2.5

    # Market confidence (0-1) — affects borrowing costs, FX, investment
    market_confidence: float = 0.65

    # Global
    global_risk: float = 0.25
    global_growth: float = 3.0

    # Player controls
    rate_override: float = 0.0
    fiscal_balance: float = -2.0
    qe_qt: float = 0.0
    tariff_rate: float = 5.0

    # Reputation / score
    reputation: float = 50.0

    # History
    history_gdp_growth: list[float] = field(default_factory=list)
    history_inflation: list[float] = field(default_factory=list)
    history_interest_rate: list[float] = field(default_factory=list)
    history_debt_gdp: list[float] = field(default_factory=list)
    history_fx: list[float] = field(default_factory=list)
    history_reputation: list[float] = field(default_factory=list)
    history_unemployment: list[float] = field(default_factory=list)
    history_confidence: list[float] = field(default_factory=list)
    history_days: list[int] = field(default_factory=list)

    # News feed
    news: list[NewsItem] = field(default_factory=list)

    # Active shocks (persisting multi-step events)
    active_shocks: list[ActiveShock] = field(default_factory=list)

    # Milestones
    milestones: list[Milestone] = field(default_factory=list)

    # Country metadata
    currency: str = "USD"
    flag: str = "🇺🇸"

    # Last triggered shock name (for banner)
    last_shock: str = ""
    last_shock_tier: int = 0

    # Consecutive recession/crisis counter
    recession_quarters: int = 0
    inflation_crisis_steps: int = 0

    # Policy change tracking (for UI feedback)
    prev_rate_override: float = 0.0
    prev_fiscal_balance: float = -2.0
    prev_qe_qt: float = 0.0
    prev_tariff_rate: float = 5.0


# ---------------------------------------------------------------------------
# Engine functions
# ---------------------------------------------------------------------------

def new_game(country_name: str) -> GameState:
    preset = COUNTRIES[country_name]
    gs = GameState(
        country_name=country_name,
        currency=preset["currency"],
        flag=preset["flag"],
        gdp=preset["gdp"],
        gdp_growth=preset["gdp_growth"],
        inflation=preset["inflation"],
        interest_rate=preset["interest_rate"],
        debt_gdp=preset["debt_gdp"],
        fx=preset["fx"],
        unemployment=preset["unemployment"],
        trade_balance=preset["trade_balance"],
        productivity=preset["productivity"],
        base_growth=preset["base_growth"],
        fiscal_balance=-2.0,
        tariff_rate=5.0,
    )
    _record_history(gs)
    return gs


def _taylor_rule_rate(gs: GameState) -> float:
    neutral_rate = 2.5
    inflation_gap = gs.inflation - 2.0
    output_gap = gs.gdp_growth - gs.base_growth
    return neutral_rate + 1.5 * inflation_gap + 0.5 * output_gap


def _record_history(gs: GameState) -> None:
    gs.history_days.append(gs.day)
    gs.history_gdp_growth.append(round(gs.gdp_growth, 3))
    gs.history_inflation.append(round(gs.inflation, 3))
    gs.history_interest_rate.append(round(gs.interest_rate, 3))
    gs.history_debt_gdp.append(round(gs.debt_gdp, 3))
    gs.history_fx.append(round(gs.fx, 4))
    gs.history_reputation.append(round(gs.reputation, 2))
    gs.history_unemployment.append(round(gs.unemployment, 3))
    gs.history_confidence.append(round(gs.market_confidence, 3))


def step(gs: GameState, days: int = 30) -> GameState:
    if gs.game_over:
        return gs

    gs.day += days
    gs.last_shock = ""
    gs.last_shock_tier = 0

    # Track policy changes for news generation
    rate_changed = abs(gs.rate_override - gs.prev_rate_override) > 0.24
    fiscal_changed = abs(gs.fiscal_balance - gs.prev_fiscal_balance) > 0.49
    gs.prev_rate_override = gs.rate_override
    gs.prev_fiscal_balance = gs.fiscal_balance
    gs.prev_qe_qt = gs.qe_qt
    gs.prev_tariff_rate = gs.tariff_rate

    # ── 1. Global environment ────────────────────────────────────────────
    gs.global_risk += random.gauss(0, 0.025)
    gs.global_risk = max(0.0, min(1.0, gs.global_risk))
    gs.global_growth += random.gauss(0, 0.12)
    gs.global_growth = max(-3.0, min(7.0, gs.global_growth))

    # ── 2. Process active shocks ─────────────────────────────────────────
    shock_inflation = 0.0
    shock_growth = 0.0
    shock_fx = 0.0
    shock_rep = 0.0
    shock_global_risk = 0.0

    still_active = []
    for shock in gs.active_shocks:
        decay = shock.steps_remaining / max(1, shock.steps_remaining + 1)  # diminishing
        shock_inflation += shock.inflation_shock * decay * 0.4
        shock_growth += shock.growth_shock * decay * 0.4
        shock_fx += shock.fx_shock * decay * 0.4
        shock_rep += shock.rep_shock * decay * 0.3
        shock_global_risk += shock.global_risk_shock * decay * 0.2
        shock.steps_remaining -= 1
        if shock.steps_remaining > 0:
            still_active.append(shock)
    gs.active_shocks = still_active

    gs.global_risk = max(0.0, min(1.0, gs.global_risk + shock_global_risk))

    # ── 3. Random new shocks ─────────────────────────────────────────────
    for event in RANDOM_EVENTS:
        daily_prob = event["probability"] / 30.0 * days
        # Tier 3/4 shocks more likely in high-risk environments
        if event["tier"] >= 3:
            daily_prob *= (1 + gs.global_risk * 2)
        if random.random() < daily_prob:
            new_shock = ActiveShock(
                name=event["name"],
                tier=event["tier"],
                steps_remaining=event.get("duration", 1),
                inflation_shock=event.get("inflation_shock", 0),
                growth_shock=event.get("growth_shock", 0),
                fx_shock=event.get("fx_shock", 0),
                rep_shock=event.get("rep_shock", 0),
                global_risk_shock=event.get("global_risk_shock", 0),
            )
            # Don't stack same shock
            if not any(s.name == new_shock.name for s in gs.active_shocks):
                gs.active_shocks.append(new_shock)
                gs.last_shock = event["name"]
                gs.last_shock_tier = event["tier"]
                # Immediate impact
                shock_inflation += event.get("inflation_shock", 0) * 0.6
                shock_growth += event.get("growth_shock", 0) * 0.6
                shock_fx += event.get("fx_shock", 0) * 0.6
                shock_rep += event.get("rep_shock", 0) * 0.5
            break

    # ── 4. Crisis cascade ────────────────────────────────────────────────
    # High inflation → confidence falls → borrowing costs rise
    if gs.inflation > 6:
        gs.inflation_crisis_steps += 1
        gs.market_confidence -= 0.04 * (days / 30.0)
    else:
        gs.inflation_crisis_steps = max(0, gs.inflation_crisis_steps - 1)

    if gs.gdp_growth < 0:
        gs.recession_quarters += 1
        gs.market_confidence -= 0.03 * (days / 30.0)
        # Trigger unemployment cascade
        if gs.recession_quarters > 3:
            shock_growth -= 0.3
    else:
        gs.recession_quarters = max(0, gs.recession_quarters - 1)

    if gs.debt_gdp > 140:
        gs.market_confidence -= 0.02 * (days / 30.0)

    # Good conditions restore confidence
    if 1.5 <= gs.inflation <= 3.0 and gs.gdp_growth > 1.5:
        gs.market_confidence += 0.015 * (days / 30.0)

    gs.market_confidence = max(0.05, min(1.0, gs.market_confidence))

    # Confidence affects borrowing spread (low confidence = higher rates)
    confidence_spread = (1.0 - gs.market_confidence) * 2.5

    # ── 5. Monetary policy ───────────────────────────────────────────────
    taylor = _taylor_rule_rate(gs)
    actual_rate = taylor + gs.rate_override
    actual_rate = max(0.0, min(25.0, actual_rate + confidence_spread * 0.3))
    gs.interest_rate = gs.interest_rate * 0.82 + actual_rate * 0.18

    rate_growth_drag = -(gs.interest_rate - taylor) * 0.03
    qe_growth_boost = gs.qe_qt * 0.012
    qe_inflation_boost = gs.qe_qt * 0.006

    # QE also affects confidence
    if gs.qe_qt > 1.5:
        gs.market_confidence += 0.01 * (days / 30.0)

    # ── 6. Fiscal policy ─────────────────────────────────────────────────
    fiscal_growth_boost = -gs.fiscal_balance * 0.015
    nominal_gdp_growth = (gs.gdp_growth + gs.inflation) / 100.0 / 12.0 * days
    debt_change = (-gs.fiscal_balance / 100.0) * (days / 365.0) * 100.0
    # Confidence affects debt costs
    debt_interest_drag = gs.debt_gdp * gs.interest_rate / 100 * (days / 365.0) * (1 + (1 - gs.market_confidence) * 0.5)
    debt_paydown = gs.debt_gdp * nominal_gdp_growth
    gs.debt_gdp += debt_change + debt_interest_drag * 0.1 - debt_paydown
    gs.debt_gdp = max(0.0, min(500.0, gs.debt_gdp))

    # ── 7. Trade / tariffs ───────────────────────────────────────────────
    tariff_trade_drag = -(gs.tariff_rate - 5.0) * 0.004
    tariff_inflation_push = (gs.tariff_rate - 5.0) * 0.003
    gs.trade_balance += tariff_trade_drag * (days / 30.0) + random.gauss(0, 0.1)
    gs.trade_balance = max(-15.0, min(15.0, gs.trade_balance))

    # ── 8. GDP growth ────────────────────────────────────────────────────
    noise = random.gauss(0, 0.15)
    gs.gdp_growth = (
        gs.base_growth
        + rate_growth_drag
        + qe_growth_boost
        + fiscal_growth_boost
        + tariff_trade_drag * 0.5
        + shock_growth
        + (gs.global_growth - 3.0) * 0.15
        + gs.productivity * 0.2 - 0.2
        + gs.market_confidence * 0.3 - 0.2  # confidence premium
        + noise
    )
    gs.gdp_growth = max(-12.0, min(15.0, gs.gdp_growth))
    gs.gdp *= (1 + gs.gdp_growth / 100.0 / 365.0) ** days

    # ── 9. Inflation (NK Phillips curve) ─────────────────────────────────
    output_gap = gs.gdp_growth - gs.base_growth
    infl_noise = random.gauss(0, 0.12)
    gs.inflation = (
        gs.inflation * 0.90
        + 0.08 * (gs.inflation + output_gap * 0.3 + tariff_inflation_push + qe_inflation_boost + shock_inflation)
        + gs.global_risk * 0.4
        + infl_noise
    )
    gs.inflation = max(-3.0, min(35.0, gs.inflation))

    # ── 10. FX ──────────────────────────────────────────────────────────
    rate_diff = gs.interest_rate - 3.5
    risk_premium = gs.global_risk * 0.04 + (1 - gs.market_confidence) * 0.02
    fx_noise = random.gauss(0, 0.005)
    fx_change = rate_diff * 0.002 - risk_premium + fx_noise + shock_fx
    if gs.country_name == "United States":
        gs.fx = 1.00
    else:
        gs.fx = max(0.001, gs.fx * (1 + fx_change * days / 30.0))

    # ── 11. Unemployment (Okun's Law) ────────────────────────────────────
    okun = -0.4 * (gs.gdp_growth - gs.base_growth)
    gs.unemployment = max(1.0, min(25.0,
        gs.unemployment + okun * (days / 365.0) + random.gauss(0, 0.05)
    ))

    # ── 12. Productivity ─────────────────────────────────────────────────
    gs.productivity += random.gauss(0, 0.002)
    # Extreme interest rates hurt investment & productivity
    if gs.interest_rate > 12:
        gs.productivity -= 0.003
    gs.productivity = max(0.7, min(1.5, gs.productivity))

    # ── 13. Reputation update ────────────────────────────────────────────
    rep_delta = 0.0

    if 1.5 <= gs.inflation <= 3.5:
        rep_delta += 1.5
    elif gs.inflation < 0:
        rep_delta -= 3.5
    elif gs.inflation > 10.0:
        rep_delta -= 6.0
    elif gs.inflation > 6.0:
        rep_delta -= 3.5
    elif gs.inflation > 4.0:
        rep_delta -= 1.5
    else:
        rep_delta -= 0.5

    if gs.gdp_growth > 3.5:
        rep_delta += 2.0
    elif gs.gdp_growth > 2.0:
        rep_delta += 1.0
    elif gs.gdp_growth > 0:
        rep_delta += 0.0
    elif gs.gdp_growth < -2.0:
        rep_delta -= 5.0
    elif gs.gdp_growth < 0:
        rep_delta -= 3.0
    else:
        rep_delta -= 1.0

    if gs.debt_gdp > 180:
        rep_delta -= 4.0
    elif gs.debt_gdp > 140:
        rep_delta -= 2.0
    elif gs.debt_gdp > 120:
        rep_delta -= 1.0
    elif gs.debt_gdp < 60:
        rep_delta += 1.0

    if gs.unemployment > 12:
        rep_delta -= 4.0
    elif gs.unemployment > 9:
        rep_delta -= 2.5
    elif gs.unemployment > 7:
        rep_delta -= 1.0
    elif gs.unemployment < 4:
        rep_delta += 0.5

    # Shock reputation hit
    rep_delta += shock_rep

    rep_delta = rep_delta * (days / 30.0)
    gs.reputation += rep_delta + random.gauss(0, 0.4)
    gs.reputation = max(0.0, min(100.0, gs.reputation))

    # ── 14. News ────────────────────────────────────────────────────────
    _generate_news(gs, rep_delta, rate_changed, fiscal_changed)

    # ── 15. Milestones ──────────────────────────────────────────────────
    _check_milestones(gs)

    # ── 16. Record history ──────────────────────────────────────────────
    _record_history(gs)

    # ── 17. Win / lose conditions ────────────────────────────────────────
    _check_end_conditions(gs)

    return gs


def _check_end_conditions(gs: GameState) -> None:
    if gs.reputation <= 0:
        gs.game_over = True
        gs.end_reason = "Your reputation collapsed — you have been removed from office."
    elif gs.inflation > 25:
        gs.game_over = True
        gs.end_reason = "Hyperinflation destroyed public trust. The economy is in freefall."
    elif gs.gdp_growth < -8 and gs.day > 90:
        gs.game_over = True
        gs.end_reason = "Catastrophic depression — parliament has dissolved your mandate."
    elif gs.debt_gdp > 280:
        gs.game_over = True
        gs.end_reason = "Sovereign debt crisis — creditors have forced a restructuring."
    elif gs.market_confidence < 0.08 and gs.day > 120:
        gs.game_over = True
        gs.end_reason = "Total market confidence collapse — capital has fled the country."
    elif gs.day >= gs.max_days:
        gs.game_over = True
        gs.game_won = True
        gs.end_reason = "You completed your full 1,200-day mandate!"


def _generate_news(gs: GameState, rep_delta: float, rate_changed: bool, fiscal_changed: bool) -> None:
    headlines = []

    # Shock news
    if gs.last_shock:
        tier_icon = TIER_COLORS.get(gs.last_shock_tier, "🟡")
        headlines.append((f"{tier_icon} BREAKING: {gs.last_shock} — markets in turmoil", "event", rep_delta * 0.5, gs.last_shock_tier))

    # Policy action news
    if rate_changed:
        if gs.rate_override > 0:
            headlines.append(("Central bank signals hawkish pivot — rate hike path confirmed", "monetary", 0.5, 1))
        else:
            headlines.append(("Dovish turn: Governor hints at rate cuts ahead", "monetary", 0.5, 1))
    if fiscal_changed:
        if gs.fiscal_balance < -4:
            headlines.append(("Fiscal stimulus unleashed — opposition warns of debt spiral", "fiscal", -0.5, 1))
        elif gs.fiscal_balance > 2:
            headlines.append(("Austerity drive: Government slashes spending", "fiscal", -0.5, 1))

    # Economic conditions
    if gs.inflation > 10:
        headlines.append(("🔴 HYPERINFLATION WARNING: Prices rising at catastrophic pace", "monetary", -5, 4))
    elif gs.inflation > 6:
        headlines.append(("🔴 CRISIS: Inflation spirals — cost of living emergency declared", "monetary", -3, 3))
    elif gs.inflation < -1:
        headlines.append(("🔴 DEFLATION SPIRAL: Falling prices signal demand collapse", "monetary", -2, 3))
    elif 1.8 <= gs.inflation <= 2.5:
        headlines.append(("✅ Markets applaud on-target inflation — credibility intact", "monetary", 1, 1))

    if gs.gdp_growth > 5:
        headlines.append(("🚀 Economic boom: Growth surges past all forecasts", "fiscal", 2, 1))
    elif gs.gdp_growth > 3.5:
        headlines.append(("Economy outperforms: Growth fuels optimism", "fiscal", 1, 1))
    elif gs.gdp_growth < -3:
        headlines.append(("🔴 SEVERE RECESSION: GDP in freefall, emergency measures debated", "fiscal", -4, 3))
    elif gs.gdp_growth < 0:
        headlines.append(("RECESSION: GDP contracts as economy enters downturn", "fiscal", -2, 2))

    if gs.debt_gdp > 200:
        headlines.append(("🔴 DEBT CRISIS: Bond vigilantes spark sovereign rating fears", "fiscal", -4, 3))
    elif gs.debt_gdp > 140:
        headlines.append(("🟠 Debt alarm: Markets demand fiscal reform plan", "fiscal", -2, 2))

    if gs.unemployment > 14:
        headlines.append(("🔴 Mass unemployment: Social unrest spreads to major cities", "fiscal", -4, 3))
    elif gs.unemployment > 10:
        headlines.append(("🟠 Jobs crisis deepens — unemployment hits double digits", "fiscal", -2, 2))
    elif gs.unemployment < 3.5:
        headlines.append(("🟡 Labour market tightens — wages rising, inflation risk grows", "monetary", -0.5, 1))

    if gs.market_confidence < 0.2:
        headlines.append(("🔴 CONFIDENCE CRISIS: Investors flee, currency under severe pressure", "event", -4, 3))
    elif gs.market_confidence > 0.85:
        headlines.append(("✅ Investor confidence at multi-year high — economy a beacon of stability", "milestone", 2, 1))

    if gs.reputation > 80 and gs.day > 60:
        headlines.append(("✅ Governor praised internationally for exceptional stewardship", "milestone", 2, 1))
    elif gs.reputation < 20:
        headlines.append(("🔴 Opposition calls for emergency confidence vote — Governor embattled", "milestone", -3, 3))

    # Active shocks summary
    if len(gs.active_shocks) >= 3:
        headlines.append(("🟠 Perfect storm: Multiple crises hitting economy simultaneously", "event", -3, 3))

    if headlines:
        weights = [abs(h[2]) + 0.1 for h in headlines]
        total = sum(weights)
        r = random.random() * total
        cum = 0
        chosen = headlines[-1]
        for h, w in zip(headlines, weights):
            cum += w
            if r <= cum:
                chosen = h
                break
        gs.news.insert(0, NewsItem(
            day=gs.day,
            headline=chosen[0],
            impact=chosen[2],
            category=chosen[1],
            tier=chosen[3] if len(chosen) > 3 else 1,
        ))
        if len(gs.news) > 40:
            gs.news = gs.news[:40]


def _check_milestones(gs: GameState) -> None:
    """Award milestones for achievements."""
    existing = {m.title for m in gs.milestones}

    def award(title: str, desc: str):
        if title not in existing:
            gs.milestones.append(Milestone(gs.day, title, desc))
            gs.reputation = min(100, gs.reputation + 2)

    if gs.day >= 365 and "One Year Survivor" not in existing:
        award("One Year Survivor", "Completed your first year without being ousted.")
    if gs.reputation >= 80 and "High Approval" not in existing:
        award("High Approval", "Reputation reached 80% — the public trusts your leadership.")
    if 1.8 <= gs.inflation <= 2.2 and gs.day > 90 and "Inflation Maestro" not in existing:
        award("Inflation Maestro", "Held inflation within 0.2% of the 2% target.")
    if gs.gdp_growth > 5 and "Growth Champion" not in existing:
        award("Growth Champion", "Achieved GDP growth above 5%.")
    if gs.debt_gdp < 60 and gs.day > 180 and "Debt Slayer" not in existing:
        award("Debt Slayer", "Reduced debt below 60% of GDP.")
    if gs.unemployment < 3 and "Full Employment" not in existing:
        award("Full Employment", "Unemployment fell below 3% — historic low.")
    if gs.market_confidence > 0.9 and "Market Darling" not in existing:
        award("Market Darling", "Market confidence exceeded 90%.")
    if len(gs.active_shocks) >= 3 and "Crisis Manager" not in existing:
        award("Crisis Manager", "Survived three simultaneous economic shocks.")


# ---------------------------------------------------------------------------
# Policy impact preview (for UI)
# ---------------------------------------------------------------------------

def policy_forecast(gs: GameState, rate_override: float, fiscal_balance: float,
                    qe_qt: float, tariff_rate: float) -> dict:
    """
    Return estimated next-step direction for each indicator given proposed policy.
    Does NOT mutate gs. Returns dict of {metric: direction_str, delta_estimate}.
    """
    taylor = _taylor_rule_rate(gs)
    proposed_rate = max(0.0, min(25.0, taylor + rate_override))
    rate_drag = -(proposed_rate - taylor) * 0.03
    fiscal_boost = -fiscal_balance * 0.015
    qe_boost = qe_qt * 0.012
    tariff_drag = -(tariff_rate - 5.0) * 0.004
    tariff_infl = (tariff_rate - 5.0) * 0.003

    growth_est = gs.base_growth + rate_drag + fiscal_boost + qe_boost + tariff_drag * 0.5
    infl_est = gs.inflation + (qe_qt * 0.006 + tariff_infl) * 0.3
    debt_est = gs.debt_gdp + (-fiscal_balance / 100.0) * (30 / 365.0) * 100.0

    def arrow(current, predicted):
        diff = predicted - current
        if diff > 0.1: return "▲"
        if diff < -0.1: return "▼"
        return "→"

    return {
        "growth_arrow": arrow(gs.gdp_growth, growth_est),
        "growth_delta": round(growth_est - gs.gdp_growth, 2),
        "inflation_arrow": arrow(gs.inflation, infl_est),
        "inflation_delta": round(infl_est - gs.inflation, 2),
        "debt_arrow": arrow(gs.debt_gdp, debt_est),
        "debt_delta": round(debt_est - gs.debt_gdp, 1),
        "proposed_rate": round(proposed_rate, 2),
        "taylor_rate": round(taylor, 2),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def final_score(gs: GameState) -> dict:
    if not gs.history_gdp_growth:
        return {}

    avg_growth = sum(gs.history_gdp_growth) / len(gs.history_gdp_growth)
    avg_inflation = sum(gs.history_inflation) / len(gs.history_inflation)
    avg_debt = sum(gs.history_debt_gdp) / len(gs.history_debt_gdp)
    avg_unemployment = sum(gs.history_unemployment) / len(gs.history_unemployment)
    days_survived = gs.day

    growth_score = min(35, max(0, (avg_growth / 3.0) * 35))
    inflation_score = min(25, max(0, 25 - abs(avg_inflation - 2.0) * 5))
    debt_score = min(15, max(0, (1 - avg_debt / 200) * 15))
    unemployment_score = min(15, max(0, (1 - (avg_unemployment - 3) / 15) * 15))
    survival_score = min(10, (days_survived / gs.max_days) * 10)
    milestone_bonus = min(10, len(gs.milestones) * 1.5)

    total = growth_score + inflation_score + debt_score + unemployment_score + survival_score + milestone_bonus

    grade = "F"
    if total >= 90: grade = "S"
    elif total >= 80: grade = "A"
    elif total >= 70: grade = "B"
    elif total >= 55: grade = "C"
    elif total >= 40: grade = "D"

    return {
        "total": round(total, 1),
        "grade": grade,
        "growth_score": round(growth_score, 1),
        "inflation_score": round(inflation_score, 1),
        "debt_score": round(debt_score, 1),
        "unemployment_score": round(unemployment_score, 1),
        "survival_score": round(survival_score, 1),
        "milestone_bonus": round(milestone_bonus, 1),
        "avg_growth": round(avg_growth, 2),
        "avg_inflation": round(avg_inflation, 2),
        "avg_debt": round(avg_debt, 1),
        "avg_unemployment": round(avg_unemployment, 1),
        "days_survived": days_survived,
        "milestones_earned": len(gs.milestones),
    }
