"""
engine.py — Global Macro simulation engine.

Pure Python / NumPy logic. Zero Streamlit / UI dependencies.
All state is stored in a single GameState dataclass so the caller
(e.g. Streamlit) owns persistence.
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
        "gdp": 100.0,           # index, starts at 100
        "gdp_growth": 2.5,      # %
        "inflation": 2.1,       # %
        "interest_rate": 5.25,  # %
        "debt_gdp": 122.0,      # %
        "fx": 1.00,             # vs USD
        "unemployment": 4.0,    # %
        "trade_balance": -3.2,  # % GDP
        "productivity": 1.0,
        "base_growth": 2.5,
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
    },
}

# ---------------------------------------------------------------------------
# Shock catalogue
# ---------------------------------------------------------------------------

RANDOM_EVENTS: list[dict] = [
    {"name": "Oil Price Spike", "inflation_shock": 0.8, "growth_shock": -0.5, "fx_shock": -0.02, "probability": 0.04},
    {"name": "Oil Price Crash", "inflation_shock": -0.6, "growth_shock": 0.3, "fx_shock": 0.01, "probability": 0.03},
    {"name": "Global Recession Signal", "inflation_shock": -0.3, "growth_shock": -1.2, "fx_shock": 0.03, "probability": 0.03},
    {"name": "Tech Sector Boom", "inflation_shock": 0.2, "growth_shock": 0.8, "fx_shock": 0.02, "probability": 0.04},
    {"name": "Banking Sector Stress", "inflation_shock": 0.1, "growth_shock": -0.9, "fx_shock": -0.04, "probability": 0.02},
    {"name": "Supply Chain Disruption", "inflation_shock": 1.0, "growth_shock": -0.6, "fx_shock": -0.01, "probability": 0.03},
    {"name": "Productivity Surge", "inflation_shock": -0.2, "growth_shock": 0.7, "fx_shock": 0.03, "probability": 0.03},
    {"name": "Capital Flight Episode", "inflation_shock": 0.5, "growth_shock": -0.8, "fx_shock": -0.06, "probability": 0.02},
    {"name": "Commodity Supercycle", "inflation_shock": 0.9, "growth_shock": 0.4, "fx_shock": 0.01, "probability": 0.02},
    {"name": "Geopolitical Shock", "inflation_shock": 0.6, "growth_shock": -0.7, "fx_shock": -0.03, "probability": 0.03},
    {"name": "Debt Ceiling Crisis", "inflation_shock": 0.3, "growth_shock": -0.5, "fx_shock": -0.02, "probability": 0.02},
    {"name": "Currency War Escalation", "inflation_shock": 0.4, "growth_shock": -0.3, "fx_shock": -0.05, "probability": 0.02},
    {"name": "Strong Jobs Report", "inflation_shock": 0.3, "growth_shock": 0.4, "fx_shock": 0.02, "probability": 0.05},
    {"name": "Weak Earnings Season", "inflation_shock": -0.1, "growth_shock": -0.4, "fx_shock": -0.01, "probability": 0.04},
    {"name": "Rating Agency Upgrade", "inflation_shock": 0.0, "growth_shock": 0.2, "fx_shock": 0.03, "probability": 0.02},
    {"name": "Rating Agency Downgrade", "inflation_shock": 0.2, "growth_shock": -0.3, "fx_shock": -0.04, "probability": 0.02},
]

# ---------------------------------------------------------------------------
# Reputation event log
# ---------------------------------------------------------------------------

@dataclass
class NewsItem:
    day: int
    headline: str
    impact: float   # reputation delta that triggered this headline
    category: str   # "monetary" | "fiscal" | "trade" | "event" | "milestone"


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
    gdp_growth: float = 2.5          # annualised %
    inflation: float = 2.1           # annualised %
    interest_rate: float = 5.25      # central bank policy rate %
    debt_gdp: float = 122.0          # %
    fx: float = 1.00                 # vs USD
    unemployment: float = 4.0        # %
    trade_balance: float = -3.2      # % GDP
    productivity: float = 1.0
    base_growth: float = 2.5         # structural potential growth

    # Global
    global_risk: float = 0.25        # chi  0-1
    global_growth: float = 3.0       # %

    # Player controls (set each turn)
    rate_override: float = 0.0       # pp above/below Taylor rule
    fiscal_balance: float = -2.0     # % GDP (negative = deficit)
    qe_qt: float = 0.0               # % GDP of asset purchases (+) / sales (-)
    tariff_rate: float = 5.0         # %

    # Reputation / score
    reputation: float = 50.0         # %

    # History series (for charting)
    history_gdp_growth: list[float] = field(default_factory=list)
    history_inflation: list[float] = field(default_factory=list)
    history_interest_rate: list[float] = field(default_factory=list)
    history_debt_gdp: list[float] = field(default_factory=list)
    history_fx: list[float] = field(default_factory=list)
    history_reputation: list[float] = field(default_factory=list)
    history_unemployment: list[float] = field(default_factory=list)
    history_days: list[int] = field(default_factory=list)

    # News feed
    news: list[NewsItem] = field(default_factory=list)

    # Country metadata
    currency: str = "USD"
    flag: str = "🇺🇸"

    # Last active shock name
    last_shock: str = ""


# ---------------------------------------------------------------------------
# Engine functions
# ---------------------------------------------------------------------------

def new_game(country_name: str) -> GameState:
    """Create a fresh GameState for the given country."""
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
    """Calculate the Taylor Rule suggested policy rate."""
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


def step(gs: GameState, days: int = 30) -> GameState:
    """
    Advance the simulation by `days` days (default 1 month).
    Mutates gs in-place and returns it.
    """
    if gs.game_over:
        return gs

    gs.day += days
    gs.last_shock = ""

    # ---- 1. Global environment drift ----
    gs.global_risk += random.gauss(0, 0.02)
    gs.global_risk = max(0.0, min(1.0, gs.global_risk))
    gs.global_growth += random.gauss(0, 0.1)
    gs.global_growth = max(-3.0, min(7.0, gs.global_growth))

    # ---- 2. Monetary policy ----
    taylor = _taylor_rule_rate(gs)
    actual_rate = taylor + gs.rate_override
    actual_rate = max(0.0, min(25.0, actual_rate))
    gs.interest_rate = gs.interest_rate * 0.85 + actual_rate * 0.15  # inertia

    # Rate effect on growth (monthly fraction)
    rate_growth_drag = -(gs.interest_rate - taylor) * 0.03
    # QE / QT effect
    qe_growth_boost = gs.qe_qt * 0.012
    qe_inflation_boost = gs.qe_qt * 0.006

    # ---- 3. Fiscal policy ----
    # Primary balance: negative = deficit → boosts growth
    fiscal_growth_boost = -gs.fiscal_balance * 0.015
    # Debt accumulates from deficit minus nominal growth paydown
    nominal_gdp_growth = (gs.gdp_growth + gs.inflation) / 100.0 / 12.0 * days
    debt_change = (-gs.fiscal_balance / 100.0) * (days / 365.0) * 100.0
    debt_paydown = gs.debt_gdp * nominal_gdp_growth
    gs.debt_gdp += debt_change - debt_paydown

    # ---- 4. Trade / tariffs ----
    tariff_trade_drag = -(gs.tariff_rate - 5.0) * 0.004
    tariff_inflation_push = (gs.tariff_rate - 5.0) * 0.003
    gs.trade_balance += tariff_trade_drag * (days / 30.0) + random.gauss(0, 0.1)
    gs.trade_balance = max(-15.0, min(15.0, gs.trade_balance))

    # ---- 5. GDP growth ----
    noise = random.gauss(0, 0.15)
    gs.gdp_growth = (
        gs.base_growth
        + rate_growth_drag
        + qe_growth_boost
        + fiscal_growth_boost
        + tariff_trade_drag * 0.5
        + (gs.global_growth - 3.0) * 0.15          # global spillover
        + gs.productivity * 0.2 - 0.2               # productivity premium
        + noise
    )
    gs.gdp_growth = max(-12.0, min(15.0, gs.gdp_growth))
    gs.gdp *= (1 + gs.gdp_growth / 100.0 / 365.0) ** days

    # ---- 6. Inflation (simplified NK Phillips curve) ----
    output_gap = gs.gdp_growth - gs.base_growth
    infl_noise = random.gauss(0, 0.12)
    gs.inflation = (
        gs.inflation * 0.90
        + 0.08 * (gs.inflation + output_gap * 0.3 + tariff_inflation_push + qe_inflation_boost)
        + gs.global_risk * 0.5
        + infl_noise
    )
    gs.inflation = max(-3.0, min(30.0, gs.inflation))

    # ---- 7. FX (UIP-style) ----
    rate_diff = gs.interest_rate - 3.5   # vs world average 3.5
    risk_premium = gs.global_risk * 0.03
    base_fx = COUNTRIES[gs.country_name]["fx"]
    fx_noise = random.gauss(0, 0.005)
    fx_change = rate_diff * 0.002 - risk_premium + fx_noise
    if gs.country_name == "United States":
        gs.fx = 1.00  # USD always 1
    else:
        gs.fx = max(0.001, gs.fx * (1 + fx_change * days / 30.0))

    # ---- 8. Unemployment (Okun's Law) ----
    okun = -0.4 * (gs.gdp_growth - gs.base_growth)
    gs.unemployment = max(1.0, min(25.0, gs.unemployment + okun * (days / 365.0) + random.gauss(0, 0.05)))

    # ---- 9. Productivity ----
    gs.productivity += random.gauss(0, 0.002)
    gs.productivity = max(0.7, min(1.5, gs.productivity))

    # ---- 10. Random shocks ----
    for event in RANDOM_EVENTS:
        daily_prob = event["probability"] / 30.0 * days
        if random.random() < daily_prob:
            gs.inflation += event.get("inflation_shock", 0)
            gs.gdp_growth += event.get("growth_shock", 0)
            if gs.country_name != "United States":
                gs.fx *= (1 + event.get("fx_shock", 0))
            gs.last_shock = event["name"]
            break  # one shock per step

    # ---- 11. Reputation update ----
    rep_delta = 0.0

    # Inflation scoring
    if 1.5 <= gs.inflation <= 3.5:
        rep_delta += 1.5
    elif gs.inflation < 0:
        rep_delta -= 3.0
    elif gs.inflation > 8.0:
        rep_delta -= 4.0
    elif gs.inflation > 5.0:
        rep_delta -= 2.0
    else:
        rep_delta -= 0.5

    # Growth scoring
    if gs.gdp_growth > 3.0:
        rep_delta += 1.5
    elif gs.gdp_growth > 1.5:
        rep_delta += 0.5
    elif gs.gdp_growth < 0:
        rep_delta -= 3.0
    elif gs.gdp_growth < 1.0:
        rep_delta -= 1.0

    # Debt scoring
    if gs.debt_gdp > 150:
        rep_delta -= 3.0
    elif gs.debt_gdp > 120:
        rep_delta -= 1.0
    elif gs.debt_gdp < 60:
        rep_delta += 0.5

    # Unemployment
    if gs.unemployment > 10:
        rep_delta -= 2.0
    elif gs.unemployment > 7:
        rep_delta -= 1.0

    rep_delta = rep_delta * (days / 30.0)
    gs.reputation += rep_delta + random.gauss(0, 0.5)
    gs.reputation = max(0.0, min(100.0, gs.reputation))

    # ---- 12. News headline generation ----
    _generate_news(gs, rep_delta)

    # ---- 13. Record history ----
    _record_history(gs)

    # ---- 14. Win / lose conditions ----
    if gs.reputation <= 0:
        gs.game_over = True
        gs.end_reason = "Your reputation collapsed — you have been removed from office."
    elif gs.inflation > 20:
        gs.game_over = True
        gs.end_reason = "Hyperinflation destroyed public trust. Economy in freefall."
    elif gs.gdp_growth < -8 and gs.day > 90:
        gs.game_over = True
        gs.end_reason = "Catastrophic depression — parliament has dissolved your mandate."
    elif gs.debt_gdp > 250:
        gs.game_over = True
        gs.end_reason = "Sovereign debt crisis — creditors have forced a restructuring."
    elif gs.day >= gs.max_days:
        gs.game_over = True
        gs.game_won = True
        gs.end_reason = "You completed your full 1,200-day mandate!"

    return gs


def _generate_news(gs: GameState, rep_delta: float) -> None:
    """Add a contextual news item based on current state."""
    headlines = []

    if gs.last_shock:
        headlines.append((f"BREAKING: {gs.last_shock} rattles markets", "event", rep_delta))

    if gs.inflation > 7:
        headlines.append(("CRISIS: Inflation spirals as prices surge across economy", "monetary", -2))
    elif gs.inflation < 0:
        headlines.append(("DEFLATION: Falling prices signal dangerous demand collapse", "monetary", -1.5))
    elif 1.8 <= gs.inflation <= 2.5:
        headlines.append(("Markets applaud on-target inflation reading", "monetary", 1))

    if gs.gdp_growth > 4:
        headlines.append(("Economy outperforms: Growth surge fuels optimism", "fiscal", 1))
    elif gs.gdp_growth < -1:
        headlines.append(("RECESSION: GDP contracts as economy enters contraction", "fiscal", -2))

    if gs.debt_gdp > 150:
        headlines.append(("Debt alarm: Bond vigilantes circle sovereign debt market", "fiscal", -1.5))

    if gs.unemployment > 10:
        headlines.append(("Jobs crisis deepens — unemployment hits double digits", "fiscal", -2))

    if gs.reputation > 75 and gs.day > 60:
        headlines.append(("Governor praised for steady hand on economic tiller", "milestone", 1))
    elif gs.reputation < 25:
        headlines.append(("Opposition calls for emergency vote of no confidence", "milestone", -2))

    if headlines:
        # pick one, weighted by how dramatic the absolute impact is
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
        ))
        if len(gs.news) > 30:
            gs.news = gs.news[:30]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def final_score(gs: GameState) -> dict:
    """Compute a final letter grade and breakdown."""
    if not gs.history_gdp_growth:
        return {}

    avg_growth = sum(gs.history_gdp_growth) / len(gs.history_gdp_growth)
    avg_inflation = sum(gs.history_inflation) / len(gs.history_inflation)
    avg_debt = sum(gs.history_debt_gdp) / len(gs.history_debt_gdp)
    days_survived = gs.day

    growth_score = min(40, max(0, (avg_growth / 3.0) * 40))
    inflation_score = min(30, max(0, 30 - abs(avg_inflation - 2.0) * 6))
    debt_score = min(20, max(0, (1 - avg_debt / 200) * 20))
    survival_score = min(10, (days_survived / gs.max_days) * 10)

    total = growth_score + inflation_score + debt_score + survival_score

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
        "survival_score": round(survival_score, 1),
        "avg_growth": round(avg_growth, 2),
        "avg_inflation": round(avg_inflation, 2),
        "avg_debt": round(avg_debt, 1),
        "days_survived": days_survived,
    }
