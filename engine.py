"""
engine.py — Global Macro Engine (Python port of MacroEngine JS)
Pure simulation logic. Zero UI dependencies.
"""

import math
import random
import time


def randn() -> float:
    """Box-Muller transform for standard normal sample."""
    u, v = 0.0, 0.0
    while u == 0:
        u = random.random()
    while v == 0:
        v = random.random()
    return math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * v)


class MacroEngine:
    DT = 0.05           # simulation time-step (days)
    REAL_TIME_PER_DAY = 2000  # ms per game-day at 1x speed
    TERM_LENGTH = 1200  # days

    # ------------------------------------------------------------------ init
    def __init__(self):
        self.time: float = 0.0
        self.running: bool = False
        self.speed: float = 1.0
        self.accumulator: float = 0.0
        self._last_frame: float | None = None
        self._last_record_step: int = -1

        # Global variables
        self.global_state = {
            "P_oil":   80.0,
            "R_world":  4.0,
            "chi":      0.0,
            # OU params
            "kappa_P":  0.02, "theta_P":  80.0, "sigma_P":  1.5,
            "kappa_chi": 0.1, "theta_chi": 0.0, "sigma_chi": 0.2,
            "kappa_R":  0.01, "theta_R":   4.0, "sigma_R":  0.05,
            # Jump components
            "J_P":  0.0,
            "J_chi": 0.0,
        }

        self.countries: dict = self._init_countries()
        self.trade_matrix: dict = self._init_trade_matrix()

        # Event system
        self.events: list = []
        self.next_event_time: float = random.random() * 20 + 10

        # Player state
        self.player_country: str | None = None
        self.reputation: float = 50.0
        self.game_over_state: dict | None = None   # {win: bool, reason: str}

        self.player_controls = {
            "rate_override":   0.0,   # % pts added to Taylor-rule target
            "fiscal_balance": -2.0,   # primary balance % GDP
            "tariff_level":    5.0,   # average tariff %
            "asset_purchases": 0.0,   # QE(+) / QT(-) $B/mo
        }

        # History (circular, max 500 samples)
        self.history: dict = {
            "time": [],
            "countries": {
                c: {"g": [], "pi": [], "d": [], "s": [], "q": [],
                    "Y_nom": [], "Y_real": [], "i": []}
                for c in self.countries
            }
        }

    # --------------------------------------------------------- initialisation
    def _init_countries(self) -> dict:
        c = {
            "United States": dict(
                Y_nom=27.72, Y_real=23.77, g=2.0, pi=2.0, i=5.25,
                s=1.0, d=108.2, q=100, rho=0.0, sigma=0.0,
                Y_pot_growth=2.0, pi_target=2.0, r_star=1.0,
                a=0.1, b=0.5, c=0.1,
                phi=0.2, kappa=0.1, eta=0.05,
                lambda_m=0.1, phi_pi=1.5, phi_y=0.5,
                debt_limit=150, fiscal_mult=0.5,
            ),
            "China": dict(
                Y_nom=17.79, Y_real=17.18, g=5.0, pi=2.5, i=3.0,
                s=7.2, d=80, q=100, rho=0.5, sigma=0.1,
                Y_pot_growth=4.5, pi_target=3.0, r_star=2.0,
                a=0.15, b=0.3, c=0.2,
                phi=0.3, kappa=0.15, eta=0.1,
                lambda_m=0.1, phi_pi=1.2, phi_y=0.5,
                debt_limit=120, fiscal_mult=0.6,
            ),
            "Euro Area": dict(
                Y_nom=17.75, Y_real=17.75, g=1.5, pi=2.0, i=4.5,
                s=0.9, d=90, q=100, rho=0.2, sigma=0.05,
                Y_pot_growth=1.2, pi_target=2.0, r_star=0.5,
                a=0.1, b=0.4, c=0.15,
                phi=0.2, kappa=0.1, eta=0.15,
                lambda_m=0.08, phi_pi=1.5, phi_y=0.5,
                debt_limit=100, fiscal_mult=0.4,
            ),
            "India": dict(
                Y_nom=4.13, Y_real=3.57, g=6.5, pi=5.0, i=6.5,
                s=83.0, d=82, q=100, rho=1.5, sigma=0.2,
                Y_pot_growth=6.5, pi_target=4.0, r_star=2.0,
                a=0.2, b=0.3, c=0.1,
                phi=0.4, kappa=0.2, eta=0.2,
                lambda_m=0.15, phi_pi=1.5, phi_y=0.5,
                debt_limit=90, fiscal_mult=0.7,
            ),
            "Japan": dict(
                Y_nom=4.61, Y_real=4.20, g=1.0, pi=1.0, i=0.1,
                s=150.0, d=250, q=100, rho=0.1, sigma=0.05,
                Y_pot_growth=0.8, pi_target=2.0, r_star=-0.5,
                a=0.1, b=0.2, c=0.1,
                phi=0.1, kappa=0.05, eta=0.15,
                lambda_m=0.05, phi_pi=1.5, phi_y=0.5,
                debt_limit=300, fiscal_mult=0.3,
            ),
            "Brazil": dict(
                Y_nom=2.17, Y_real=2.18, g=2.0, pi=4.5, i=10.0,
                s=5.0, d=85, q=100, rho=2.5, sigma=0.3,
                Y_pot_growth=2.0, pi_target=3.25, r_star=4.0,
                a=0.2, b=0.4, c=0.15,
                phi=0.5, kappa=0.25, eta=0.1,
                lambda_m=0.2, phi_pi=1.8, phi_y=0.5,
                debt_limit=100, fiscal_mult=0.5,
            ),
            "Russia": dict(
                Y_nom=2.02, Y_real=0.49, g=1.5, pi=6.0, i=15.0,
                s=90.0, d=20, q=100, rho=4.0, sigma=0.5,
                Y_pot_growth=1.0, pi_target=4.0, r_star=3.0,
                a=0.15, b=0.2, c=0.1,
                phi=0.4, kappa=0.2, eta=-0.3,
                lambda_m=0.2, phi_pi=1.5, phi_y=0.5,
                debt_limit=50, fiscal_mult=0.4,
            ),
            "Saudi Arabia": dict(
                Y_nom=1.07, Y_real=1.07, g=3.0, pi=2.5, i=5.0,
                s=3.75, d=30, q=100, rho=0.8, sigma=0.1,
                Y_pot_growth=2.5, pi_target=2.0, r_star=1.5,
                a=0.2, b=0.1, c=0.3,
                phi=0.3, kappa=0.1, eta=-0.5,
                lambda_m=0.1, phi_pi=1.2, phi_y=0.2,
                debt_limit=60, fiscal_mult=0.6,
            ),
        }
        for v in c.values():
            v["s_fair"] = v["s"]
        return c

    def _init_trade_matrix(self) -> dict:
        names = list(self.countries.keys())
        return {i: {j: 0.1 for j in names if j != i} for i in names}

    # --------------------------------------------------------- public control
    def set_player_country(self, name: str):
        if name in self.countries:
            self.player_country = name
            self.player_controls["rate_override"]   = 0.0
            self.player_controls["fiscal_balance"]  = -2.0
            self.player_controls["tariff_level"]    = 5.0
            self.player_controls["asset_purchases"] = 0.0

    def start(self):
        self.running = True
        self._last_frame = time.perf_counter()

    def pause(self):
        self.running = False

    def set_speed(self, s: float):
        self.speed = max(0.1, min(10.0, s))

    # --------------------------------------------------------- game loop tick
    def tick(self):
        """Call once per real frame. Advances simulation by elapsed time."""
        if not self.running:
            return
        now = time.perf_counter()
        if self._last_frame is None:
            self._last_frame = now
        delta_ms = (now - self._last_frame) * 1000
        self._last_frame = now

        ms_per_day = self.REAL_TIME_PER_DAY / self.speed
        days_to_advance = delta_ms / ms_per_day
        self.accumulator += days_to_advance

        while self.accumulator >= self.DT:
            self._update(self.DT)
            self.accumulator -= self.DT

    # ------------------------------------------------------- simulation steps
    def _update(self, dt: float):
        self._update_global(dt)
        for name, c in self.countries.items():
            self._update_country(name, c, dt)
        self._update_reputation(dt)
        self._handle_events(dt)
        self._check_game_over()
        self._record_history()
        self.time += dt

    def _update_global(self, dt: float):
        g = self.global_state
        sqrt_dt = math.sqrt(dt)

        # Oil price (OU + jump)
        dP = (g["kappa_P"] * (g["theta_P"] - g["P_oil"]) * dt
              + g["sigma_P"] * randn() * sqrt_dt
              + g["J_P"] * dt)
        g["P_oil"] = max(10.0, g["P_oil"] + dP)
        g["J_P"] *= 0.9

        # Global risk / VIX-like chi
        dChi = (-g["kappa_chi"] * (g["chi"] - g["theta_chi"]) * dt
                + g["sigma_chi"] * randn() * sqrt_dt
                + g["J_chi"] * dt)
        g["chi"] = max(0.0, g["chi"] + dChi)
        g["J_chi"] *= 0.9

        # World risk-free rate
        dR = (g["kappa_R"] * (g["theta_R"] - g["R_world"]) * dt
              + g["sigma_R"] * randn() * sqrt_dt)
        g["R_world"] += dR

    def _update_country(self, name: str, c: dict, dt: float):
        g = self.global_state
        sqrt_dt = math.sqrt(dt)
        is_player = (name == self.player_country)
        is_us     = (name == "United States")

        # 1. Output growth (IS-curve)
        real_rate = c["i"] - c["pi"]
        rate_gap  = real_rate - c["r_star"]
        fx_comp   = 0.0 if is_us else math.log(max(1e-9, c["s"] / c["s_fair"]))
        tariff_drag = (self.player_controls["tariff_level"] - 5) * 0.1 if is_player else 0.0
        nx_shock   = 0.1 * fx_comp - tariff_drag

        dg = -c["a"] * (c["g"] - c["Y_pot_growth"]) - c["b"] * rate_gap + c["c"] * nx_shock
        growth_noise = 0.5 * randn() * sqrt_dt

        fiscal_impulse = 0.0
        if is_player:
            deficit_excess = -self.player_controls["fiscal_balance"] - 2.0
            fiscal_impulse = deficit_excess * c["fiscal_mult"] * 0.1

        c["g"] += dg * dt + growth_noise + fiscal_impulse * dt

        # Update GDP levels
        c["Y_real"] *= 1 + (c["g"] / 100) * (dt / 365)
        c["Y_nom"]  *= 1 + ((c["g"] + c["pi"]) / 100) * (dt / 365)

        # 2. Inflation (Phillips curve)
        output_gap = c["g"] - c["Y_pot_growth"]
        oil_change = (g["P_oil"] - 80) / 80
        dpi = (-c["phi"] * (c["pi"] - c["pi_target"])
               + c["kappa"] * output_gap
               + c["eta"] * oil_change)
        c["pi"] += dpi * dt + 0.2 * randn() * sqrt_dt

        # 3. Monetary policy (Taylor rule + player override)
        i_target = (c["r_star"] + c["pi"]
                    + c["phi_pi"] * (c["pi"] - c["pi_target"])
                    + c["phi_y"] * output_gap)
        if is_player:
            i_target += self.player_controls["rate_override"]
        di = -c["lambda_m"] * (c["i"] - i_target)
        c["i"] = max(0.0, c["i"] + di * dt)   # Zero lower bound

        # 4. Debt dynamics (snowball effect)
        pb = self.player_controls["fiscal_balance"] if is_player else -2.0
        snowball = ((c["i"] - c["pi"]) - c["g"]) / 100 * c["d"]
        deficit_contribution = -pb
        c["d"] = max(0.0, c["d"] + (snowball + deficit_contribution) * dt)

        # 5. Risk premium / spread
        debt_excess = max(0.0, c["d"] - c["debt_limit"])
        risk_local  = min(20.0, 0.02 * debt_excess)
        risk_global = 0.0 if is_us else g["chi"] * 1.0

        qe_spread = 0.0
        if is_player:
            qe_spread = -(self.player_controls["asset_purchases"] / 10) * 0.05

        target_rho = risk_local + risk_global + c["sigma"] + qe_spread
        c["rho"] += 0.2 * (target_rho - c["rho"]) * dt
        c["rho"] = max(0.0, c["rho"])

        # 6. FX (UIP + PPP fair value pull)
        dt_years = dt / 365
        if not is_us:
            i_us  = self.countries["United States"]["i"]
            pi_us = self.countries["United States"]["pi"]
            c["s_fair"] *= 1 + (c["pi"] - pi_us) / 100 * dt_years
            carry_flow    = -(c["i"] - i_us - c["rho"]) / 100
            valuation_pull = 0.5 * math.log(max(1e-9, c["s_fair"] / c["s"]))
            drift_s = carry_flow + valuation_pull
            vol_s   = 0.1
            c["s"] *= (1 + drift_s * dt_years + vol_s * randn() * math.sqrt(dt_years))
            c["s"] = max(1e-4, c["s"])

        # 7. Equities
        qe_equity = 0.0
        if is_player:
            qe_equity = (self.player_controls["asset_purchases"] / 10) * 0.01
        equity_return = (0.05
                         + 1.0 * output_gap / 100
                         - 0.5 * (c["i"] - c["pi"]) / 100
                         - 0.5 * c["rho"] / 100
                         + qe_equity)
        vol_q = 0.15 + 0.5 * g["chi"]
        c["q"] *= (1 + equity_return * dt_years + vol_q * randn() * math.sqrt(dt_years))
        c["q"] = max(0.01, c["q"])

    def _update_reputation(self, dt: float):
        if not self.player_country:
            return
        c = self.countries[self.player_country]
        delta = 0.0
        if c["g"] > 2.0:
            delta += 0.05
        elif c["g"] < 0:
            delta -= 0.10
        if c["pi"] > 5.0:
            delta -= 0.10
        if c["pi"] > 10.0:
            delta -= 0.20
        if c["d"] > 100:
            delta -= 0.05
        if c["d"] > 150:
            delta -= 0.10
        self.reputation = min(100.0, max(0.0, self.reputation + delta * dt))

    def _handle_events(self, dt: float):
        if self.time >= self.next_event_time:
            self._trigger_random_event()
            self.next_event_time = self.time + random.random() * 40 + 40

    def _trigger_random_event(self):
        r = random.random()
        msg = ""

        if r < 0.10:
            if random.random() > 0.5:
                shock = (1 if random.random() > 0.5 else -1) * 20
                self.global_state["J_P"] = shock
                msg = ("🛢️ Oil Supply Shock! Prices Spiking."
                       if shock > 0 else "📉 Oil Price Collapse!")
            else:
                self.global_state["J_chi"] = 2.0
                msg = "📉 Global Market Panic! Risk-off sentiment prevails."

        elif r < 0.30:
            names   = list(self.countries.keys())
            target  = random.choice(names)
            is_boom = random.random() > 0.5
            if is_boom:
                self.countries[target]["g"] += 1.0
                msg = f"🚀 Tech breakthrough in {target}! Growth outlook upgraded."
            else:
                self.countries[target]["sigma"] += 1.5
                msg = f"⚠️ Credit Watch: {target} outlook negative."
                # Schedule sigma restoration via a flag (simple approach)
                self._sigma_restore_queue = getattr(self, "_sigma_restore_queue", [])
                self._sigma_restore_queue.append(
                    {"country": target, "restore_at": self.time + 80, "amount": 1.5}
                )
        else:
            flavor = [
                "G20 Summit concludes with vague promises of cooperation.",
                "IMF releases updated World Economic Outlook.",
                "Davos: Billionaires discuss inequality over canapés.",
                "Protests erupt in emerging markets over food prices.",
                "Central Bank Governors meet in Jackson Hole.",
                "New trade deal signed between regional powers.",
                "Tech sector regulation talks stall in parliament.",
                "Climate accord signed, markets react with indifference.",
                "Election season heats up in major economies.",
                "Supply chain bottlenecks reported at major ports.",
                "Youth unemployment figures spark parliamentary debate.",
                "Consumer confidence index hits a 6-month high.",
            ]
            msg = "📰 " + random.choice(flavor)

        self.events.insert(0, {"time": self.time, "text": msg})
        if len(self.events) > 10:
            self.events.pop()

        # Process sigma restore queue
        queue = getattr(self, "_sigma_restore_queue", [])
        still_pending = []
        for item in queue:
            if self.time >= item["restore_at"]:
                self.countries[item["country"]]["sigma"] = max(
                    0.0, self.countries[item["country"]]["sigma"] - item["amount"]
                )
            else:
                still_pending.append(item)
        self._sigma_restore_queue = still_pending

    def _check_game_over(self):
        if not self.running:
            return
        if self.time >= self.TERM_LENGTH:
            self.running = False
            self.game_over_state = {"win": True,  "reason": self._rand_msg("win")}
        elif self.reputation <= 0:
            self.running = False
            self.game_over_state = {"win": False, "reason": self._rand_msg("loss")}

    def _rand_msg(self, kind: str) -> str:
        wins = [
            "Re-elected in a landslide! The people love you.",
            "Statue erected in your honour. A golden age!",
            "History will remember you as 'The Great'.",
            "Retired peacefully to a private island. Mission accomplished.",
            "Nobel Prize in Economics awarded for your stewardship.",
        ]
        losses = [
            "Coup d'état! The military has seized the palace.",
            "Vote of No Confidence passed. You are out.",
            "Impeached for gross incompetence. Shame!",
            "Forced to resign amidst mass protests.",
            "The economy collapsed, and so did your government.",
        ]
        pool = wins if kind == "win" else losses
        return random.choice(pool)

    def _record_history(self):
        record_step = 0.2
        current_step = int(self.time / record_step)
        if current_step <= self._last_record_step:
            return
        self._last_record_step = current_step

        self.history["time"].append(self.time)
        for name, c in self.countries.items():
            h = self.history["countries"][name]
            h["g"].append(c["g"])
            h["pi"].append(c["pi"])
            h["d"].append(c["d"])
            h["s"].append(c["s"])
            h["q"].append(c["q"])
            h["Y_nom"].append(c["Y_nom"])
            h["Y_real"].append(c["Y_real"])
            h["i"].append(c["i"])

        # Keep last 500 samples
        if len(self.history["time"]) > 500:
            self.history["time"].pop(0)
            for ch in self.history["countries"].values():
                for lst in ch.values():
                    lst.pop(0)
