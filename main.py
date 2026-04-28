"""
ui.py — UIController for Global Macro (Python/pygame port)
All rendering, input, and chart drawing. Engine is injected; no simulation logic here.
"""

import math
import pygame
import pygame.gfxdraw


# ─────────────────────────── Colour palette (mirrors CSS vars) ──────────────
BG_DARK   = (5,   5,   5)
BG_PANEL  = (10,  10,  10)
BG_LIGHT  = (17,  17,  17)
BG_DARKER = (0,   0,   0)
PRIMARY   = (0,   255, 136)   # neon green
SECONDARY = (255, 51,  51)    # neon red
ACCENT    = (0,   204, 255)   # neon blue
TEXT_PRI  = (224, 224, 224)
TEXT_SEC  = (136, 136, 136)
BORDER    = (34,  34,  34)
GRID_LINE = (26,  26,  26)
YELLOW    = (255, 255,  51)
PINK      = (255, 153, 204)
MAGENTA   = (255,  0,  255)
GRAY      = (153, 153, 153)
LIME      = (51,  255,  51)
GOLD      = (204, 153,   0)

COUNTRY_COLORS = {
    "United States": ACCENT,
    "China":         SECONDARY,
    "Euro Area":     YELLOW,
    "India":         MAGENTA,
    "Japan":         PINK,
    "Brazil":        LIME,
    "Russia":        GRAY,
    "Saudi Arabia":  GOLD,
}

FLAGS = {
    "United States": "🇺🇸", "China": "🇨🇳", "Euro Area": "🇪🇺",
    "India": "🇮🇳", "Japan": "🇯🇵", "Brazil": "🇧🇷",
    "Russia": "🇷🇺", "Saudi Arabia": "🇸🇦",
}


# ─────────────────────────── tiny helpers ───────────────────────────────────
def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Button:
    """Simple clickable rectangle."""
    def __init__(self, rect, label, color=PRIMARY, text_color=BG_DARK):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, surf, font):
        col = lerp_color(self.color, (255, 255, 255), 0.25) if self.hovered else self.color
        pygame.draw.rect(surf, BG_LIGHT, self.rect)
        pygame.draw.rect(surf, col, self.rect, 1)
        txt = font.render(self.label, True, col)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            return True
        return False


# ─────────────────────────── chart helper ───────────────────────────────────
def draw_line_chart(surf, rect, data: list, color, y_label="", bg=BG_PANEL):
    """Draw a simple line chart inside `rect` on `surf`."""
    x, y, w, h = rect
    pygame.draw.rect(surf, bg, rect)
    pygame.draw.rect(surf, BORDER, rect, 1)

    if len(data) < 2:
        return

    mn, mx = min(data), max(data)
    spread = mx - mn
    if spread < 1e-6:
        spread = 1.0
        mn -= 0.5

    pad = 4
    iw = w - pad * 2
    ih = h - pad * 2

    pts = []
    for i, v in enumerate(data):
        px = x + pad + int(i / (len(data) - 1) * iw)
        py = y + pad + ih - int((v - mn) / spread * ih)
        pts.append((px, py))

    # grid line at zero if visible
    if mn < 0 < mx:
        zy = y + pad + ih - int((0 - mn) / spread * ih)
        pygame.draw.line(surf, GRID_LINE, (x + pad, zy), (x + pad + iw, zy), 1)

    # polygon fill (alpha-ish: draw dark fill)
    if len(pts) >= 2:
        poly = [pts[0]] + pts + [(pts[-1][0], y + h - pad), (pts[0][0], y + h - pad)]
        fill_col = (color[0] // 8, color[1] // 8, color[2] // 8)
        pygame.draw.polygon(surf, fill_col, poly)
        pygame.draw.lines(surf, color, False, pts, 2)

    # min/max labels (tiny)
    try:
        ft = pygame.font.SysFont("monospace", 8)
        surf.blit(ft.render(f"{mx:.1f}", True, TEXT_SEC), (x + pad, y + pad))
        surf.blit(ft.render(f"{mn:.1f}", True, TEXT_SEC), (x + pad, y + h - pad - 10))
        if y_label:
            surf.blit(ft.render(y_label, True, TEXT_SEC), (x + pad + 2, y + pad + 12))
    except Exception:
        pass


# ─────────────────────────── main UI class ──────────────────────────────────
class UIController:
    WIN_W = 1400
    WIN_H = 820
    FPS   = 60

    LEFT_W    = 250
    RIGHT_W   = 310
    HDR_H     = 60
    BOT_H     = 50
    PAD       = 10

    def __init__(self, engine):
        self.engine = engine
        pygame.init()
        pygame.display.set_caption("GLOBAL MACRO")
        self.screen = pygame.display.set_mode((self.WIN_W, self.WIN_H))
        self.clock  = pygame.time.Clock()

        # Fonts
        self.font_mono_sm  = pygame.font.SysFont("monospace",  9)
        self.font_mono_med = pygame.font.SysFont("monospace", 11)
        self.font_mono_lg  = pygame.font.SysFont("monospace", 14)
        self.font_mono_xl  = pygame.font.SysFont("monospace", 18, bold=True)
        self.font_ui       = pygame.font.SysFont("sans",      11)

        # Layout rects
        self._compute_rects()

        # Screens
        self.mode = "select"   # "select" | "game" | "gameover"
        self.selected_country: str | None = None
        self.game_over_shown = False

        # Build selection screen buttons
        self._build_select_buttons()

        # Build control buttons (game screen)
        self._build_control_buttons()

        # Tooltip
        self.tooltip_country: str | None = None
        self.tooltip_pos = (0, 0)

        # Game-over state cache
        self.go_msg = ""
        self.go_win = False

    # ─────────────────────────── layout ─────────────────────────────────────
    def _compute_rects(self):
        W, H = self.WIN_W, self.WIN_H
        P = self.PAD

        self.hdr_rect   = pygame.Rect(P, P, W - 2*P, self.HDR_H)
        self.bot_rect   = pygame.Rect(P, H - self.BOT_H - P, W - 2*P, self.BOT_H)

        inner_y = self.hdr_rect.bottom + P
        inner_h = self.bot_rect.top - inner_y - P

        self.left_rect  = pygame.Rect(P, inner_y, self.LEFT_W, inner_h)
        self.right_rect = pygame.Rect(W - self.RIGHT_W - P, inner_y, self.RIGHT_W, inner_h)

        mid_x = self.left_rect.right + P
        mid_w = self.right_rect.left - mid_x - P
        self.mid_rect   = pygame.Rect(mid_x, inner_y, mid_w, inner_h)

        # 4 charts in 2×2 grid
        cw = self.mid_rect.width  // 2 - 1
        ch = self.mid_rect.height // 2 - 1
        mx, my = self.mid_rect.x, self.mid_rect.y
        self.chart_rects = [
            pygame.Rect(mx,       my,       cw, ch),
            pygame.Rect(mx+cw+2,  my,       cw, ch),
            pygame.Rect(mx,       my+ch+2,  cw, ch),
            pygame.Rect(mx+cw+2,  my+ch+2,  cw, ch),
        ]
        self.chart_labels = ["GDP GROWTH (%)", "INFLATION (%)", "DEBT / GDP (%)", "FX / USD"]
        self.chart_keys   = ["g", "pi", "d", "s"]

    def _build_select_buttons(self):
        self.select_buttons: dict[str, pygame.Rect] = {}
        names = list(self.engine.countries.keys())
        cols, rows = 4, 2
        bw, bh = 160, 80
        total_w = cols * bw + (cols - 1) * 10
        total_h = rows * bh + (rows - 1) * 10
        sx = (self.WIN_W - total_w) // 2
        sy = (self.WIN_H - total_h) // 2 + 40
        for i, name in enumerate(names):
            col, row = i % cols, i // cols
            rx = sx + col * (bw + 10)
            ry = sy + row * (bh + 10)
            self.select_buttons[name] = pygame.Rect(rx, ry, bw, bh)

    def _build_control_buttons(self):
        rx = self.right_rect.x + self.PAD
        ry = self.right_rect.y + self.PAD

        bw, bh = 40, 22

        # Layout helpers: arranged vertically inside right panel
        # We'll position them during draw since we don't know right_rect until layout.
        # Store as relative offsets; resolve in draw.
        self.ctrl_buttons: dict[str, Button] = {}

        # Playback row (bottom bar)
        bbot = self.bot_rect
        self.ctrl_buttons["start"]   = Button((bbot.x + 10,           bbot.y + 14, 70, 22), "START",  PRIMARY)
        self.ctrl_buttons["pause"]   = Button((bbot.x + 90,           bbot.y + 14, 70, 22), "PAUSE",  SECONDARY)
        self.ctrl_buttons["spd_dn"]  = Button((bbot.right - 130,      bbot.y + 14, 30, 22), " - ",    BORDER)
        self.ctrl_buttons["spd_up"]  = Button((bbot.right - 60,       bbot.y + 14, 30, 22), " + ",    BORDER)

        # Policy controls inside right panel (built dynamically in draw)

    # ─────────────────────────── main loop ───────────────────────────────────
    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False
                self._handle_event(ev)

            # Advance simulation
            self.engine.tick()

            # Check for game-over
            if self.engine.game_over_state and not self.game_over_shown:
                self.go_win = self.engine.game_over_state["win"]
                self.go_msg = self.engine.game_over_state["reason"]
                self.mode = "gameover"
                self.game_over_shown = True

            # Draw
            self.screen.fill(BG_DARKER)
            if self.mode == "select":
                self._draw_select()
            elif self.mode == "game":
                self._draw_game()
            elif self.mode == "gameover":
                self._draw_game()       # draw game behind overlay
                self._draw_gameover()

            pygame.display.flip()
            self.clock.tick(self.FPS)

        pygame.quit()

    # ─────────────────────────── input ──────────────────────────────────────
    def _handle_event(self, ev):
        if self.mode == "select":
            self._handle_select(ev)
        elif self.mode == "game":
            self._handle_game(ev)
        elif self.mode == "gameover":
            if ev.type == pygame.KEYDOWN or (ev.type == pygame.MOUSEBUTTONDOWN):
                self.mode = "game"   # dismiss overlay

    def _handle_select(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for name, rect in self.select_buttons.items():
                if rect.collidepoint(ev.pos):
                    self.selected_country = name
                    self.engine.set_player_country(name)
                    self.mode = "game"

    def _handle_game(self, ev):
        # Tooltip
        if ev.type == pygame.MOUSEMOTION:
            self.tooltip_country = None
            self.tooltip_pos = ev.pos
            for name, rect in self._country_row_rects.items():
                if rect.collidepoint(ev.pos):
                    self.tooltip_country = name

        # Bottom-bar buttons
        if self.ctrl_buttons["start"].handle(ev):
            if not self.engine.running:
                self.engine.start()
        if self.ctrl_buttons["pause"].handle(ev):
            if self.engine.running:
                self.engine.pause()
            else:
                self.engine.start()
        if self.ctrl_buttons["spd_dn"].handle(ev):
            self.engine.set_speed(self.engine.speed - 0.5)
        if self.ctrl_buttons["spd_up"].handle(ev):
            self.engine.set_speed(self.engine.speed + 0.5)

        # Policy buttons (detected by tag)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            pc = self.engine.player_controls
            for tag, rect in self._policy_button_rects.items():
                if rect.collidepoint(ev.pos):
                    if tag == "rate_dn":
                        pc["rate_override"] = clamp(pc["rate_override"] - 0.25, -5.0, 5.0)
                    elif tag == "rate_up":
                        pc["rate_override"] = clamp(pc["rate_override"] + 0.25, -5.0, 5.0)
                    elif tag == "fis_dn":
                        pc["fiscal_balance"] = clamp(round(pc["fiscal_balance"] - 0.1, 1), -10, 5)
                    elif tag == "fis_up":
                        pc["fiscal_balance"] = clamp(round(pc["fiscal_balance"] + 0.1, 1), -10, 5)
                    elif tag == "tar_dn":
                        pc["tariff_level"] = clamp(pc["tariff_level"] - 1, 0, 50)
                    elif tag == "tar_up":
                        pc["tariff_level"] = clamp(pc["tariff_level"] + 1, 0, 50)
                    elif tag == "qt":
                        pc["asset_purchases"] = clamp(pc["asset_purchases"] - 10, -200, 500)
                    elif tag == "qe":
                        pc["asset_purchases"] = clamp(pc["asset_purchases"] + 10, -200, 500)

    # ─────────────────────────── SELECT SCREEN ───────────────────────────────
    def _draw_select(self):
        s = self.screen
        s.fill(BG_DARK)

        title = self.font_mono_xl.render("GLOBAL MACRO — SELECT YOUR SOVEREIGN", True, PRIMARY)
        s.blit(title, title.get_rect(centerx=self.WIN_W // 2, y=80))

        sub = self.font_ui.render(
            "Choose the nation you will guide through turbulent tides of the global economy.",
            True, TEXT_SEC
        )
        s.blit(sub, sub.get_rect(centerx=self.WIN_W // 2, y=120))

        mx, my = pygame.mouse.get_pos()
        for name, rect in self.select_buttons.items():
            hov = rect.collidepoint(mx, my)
            border_col = PRIMARY if hov else BORDER
            bg_col     = (20, 30, 20) if hov else BG_PANEL
            pygame.draw.rect(s, bg_col, rect)
            pygame.draw.rect(s, border_col, rect, 1)

            flag_txt = self.font_mono_xl.render(name[:2], True, ACCENT)  # fallback
            # Render name
            nm = self.font_mono_med.render(name, True, TEXT_PRI if not hov else PRIMARY)
            s.blit(nm, nm.get_rect(centerx=rect.centerx, y=rect.y + 14))

            # Country stats mini preview
            c = self.engine.countries[name]
            stat = self.font_mono_sm.render(
                f"g:{c['g']:.1f}%  π:{c['pi']:.1f}%  d:{c['d']:.0f}%",
                True, TEXT_SEC
            )
            s.blit(stat, stat.get_rect(centerx=rect.centerx, y=rect.y + 46))

    # ─────────────────────────── GAME SCREEN ─────────────────────────────────
    def _draw_game(self):
        s = self.screen
        self._country_row_rects = {}   # reset for hit-testing
        self._policy_button_rects = {}

        self._draw_header(s)
        self._draw_left_panel(s)
        self._draw_charts(s)
        self._draw_right_panel(s)
        self._draw_bottom_bar(s)
        if self.tooltip_country:
            self._draw_tooltip(s)

    def _draw_header(self, s):
        r = self.hdr_rect
        pygame.draw.rect(s, BG_PANEL, r)
        pygame.draw.rect(s, BORDER, r, 1)

        title = self.font_mono_xl.render("GLOBAL MACRO", True, PRIMARY)
        s.blit(title, (r.x + 15, r.y + (r.h - title.get_height()) // 2))

        # Ticker
        tx = r.x + 180
        ty = r.y + (r.h - 10) // 2
        items = [
            ("OIL",    f"${self.engine.global_state['P_oil']:.2f}"),
            ("RISK",   f"{self.engine.global_state['chi']:.2f}"),
            ("US 10Y", f"{self.engine.global_state['R_world']:.2f}%"),
        ]
        for label, val in items:
            lbl = self.font_mono_sm.render(label, True, TEXT_SEC)
            v   = self.font_mono_sm.render(val,   True, PRIMARY)
            s.blit(lbl, (tx, ty)); tx += lbl.get_width() + 4
            s.blit(v,   (tx, ty)); tx += v.get_width() + 18

        # Right side
        day_txt = self.font_mono_med.render(
            f"Day {int(self.engine.time)} / {self.engine.TERM_LENGTH}", True, ACCENT
        )
        s.blit(day_txt, (r.right - day_txt.get_width() - 150, r.y + 12))

        if self.selected_country:
            pc_txt = self.font_mono_sm.render(
                f"Managing: {self.selected_country}", True, TEXT_PRI
            )
            s.blit(pc_txt, (r.right - pc_txt.get_width() - 15, r.y + 32))

    def _draw_left_panel(self, s):
        r = self.left_rect
        pygame.draw.rect(s, BG_PANEL, r)
        pygame.draw.rect(s, BORDER, r, 1)

        hdr = self.font_mono_sm.render("MARKET MONITOR", True, TEXT_SEC)
        s.blit(hdr, (r.x + 8, r.y + 8))
        pygame.draw.line(s, BORDER, (r.x, r.y + 24), (r.right, r.y + 24))

        cy = r.y + 30
        for name, c in self.engine.countries.items():
            row_rect = pygame.Rect(r.x, cy, r.width, 28)
            self._country_row_rects[name] = row_rect

            is_player = (name == self.selected_country)
            bg = (0, 30, 15) if is_player else BG_PANEL
            pygame.draw.rect(s, bg, row_rect)
            if is_player:
                pygame.draw.line(s, PRIMARY, (r.x, cy), (r.x, cy + 28), 2)

            # Name
            col = PRIMARY if is_player else TEXT_PRI
            nm = self.font_mono_sm.render(name[:14], True, col)
            s.blit(nm, (r.x + 10, cy + 9))

            # Growth
            g = c["g"]
            g_col = PRIMARY if g >= 0 else SECONDARY
            g_txt = self.font_mono_sm.render(f"{g:+.1f}%", True, g_col)
            s.blit(g_txt, (r.right - g_txt.get_width() - 6, cy + 9))

            pygame.draw.line(s, BORDER, (r.x, cy + 28), (r.right, cy + 28))
            cy += 28

    def _draw_charts(self, s):
        if not self.selected_country:
            return
        h = self.engine.history
        c = self.selected_country
        color = COUNTRY_COLORS.get(c, TEXT_PRI)

        for i, (rect, label, key) in enumerate(
            zip(self.chart_rects, self.chart_labels, self.chart_keys)
        ):
            data = h["countries"][c][key]
            pygame.draw.rect(s, BG_PANEL, rect)
            pygame.draw.rect(s, BORDER, rect, 1)

            lbl = self.font_mono_sm.render(label, True, TEXT_SEC)
            s.blit(lbl, (rect.x + 5, rect.y + 4))

            inner = pygame.Rect(rect.x + 2, rect.y + 16, rect.width - 4, rect.height - 20)
            draw_line_chart(s, inner, data, color, bg=BG_PANEL)

    def _draw_right_panel(self, s):
        r = self.right_rect
        pygame.draw.rect(s, BG_PANEL, r)
        pygame.draw.rect(s, BORDER, r, 1)

        hdr = self.font_mono_sm.render("COMMAND CENTER", True, TEXT_SEC)
        s.blit(hdr, (r.x + 8, r.y + 8))
        pygame.draw.line(s, BORDER, (r.x, r.y + 24), (r.right, r.y + 24))

        cy = r.y + 30

        # ── Dashboard ──
        if self.selected_country:
            pc = self.engine.countries[self.selected_country]
            rep = self.engine.reputation
            rep_col = PRIMARY if rep > 50 else (TEXT_PRI if rep > 25 else SECONDARY)

            dash = [
                ("REPUTATION",  f"{rep:.1f}%",          rep_col),
                ("REAL GDP",    f"${pc['Y_real']:.2f}T", TEXT_PRI),
                ("NOM GDP",     f"${pc['Y_nom']:.2f}T",  TEXT_PRI),
                ("GROWTH",      f"{pc['g']:.2f}%",       PRIMARY if pc['g'] >= 0 else SECONDARY),
                ("INFLATION",   f"{pc['pi']:.2f}%",      PRIMARY if pc['pi'] <= 2 else SECONDARY),
                ("DEBT/GDP",    f"{pc['d']:.1f}%",       PRIMARY if pc['d'] < 100 else SECONDARY),
                ("RATE",        f"{pc['i']:.2f}%",       ACCENT),
            ]
            pygame.draw.rect(s, BG_LIGHT, (r.x, cy, r.width, len(dash) * 18 + 6))
            for label, val, col in dash:
                lbl = self.font_mono_sm.render(label, True, TEXT_SEC)
                v   = self.font_mono_sm.render(val,   True, col)
                s.blit(lbl, (r.x + 8,            cy + 3))
                s.blit(v,   (r.right - v.get_width() - 8, cy + 3))
                cy += 18
            cy += 6
            pygame.draw.line(s, BORDER, (r.x, cy), (r.right, cy))
            cy += 8

        # ── Policy Controls ──
        pc_ctrl = self.engine.player_controls
        controls = [
            ("RATE OVERRIDE (bps)",     "rate_override",   "rate_dn",  "rate_up",
             f"{pc_ctrl['rate_override']*100:+.0f}"),
            ("ASSET PURCHASES ($B/mo)", "asset_purchases", "qt",       "qe",
             f"{pc_ctrl['asset_purchases']:+.0f}"),
            ("FISCAL BALANCE (% GDP)",  "fiscal_balance",  "fis_dn",   "fis_up",
             f"{pc_ctrl['fiscal_balance']:.1f}"),
            ("TARIFF LEVEL (%)",        "tariff_level",    "tar_dn",   "tar_up",
             f"{pc_ctrl['tariff_level']:.0f}"),
        ]

        bw, bh = 42, 20
        for cfg_label, _, tag_dn, tag_up, display_val in controls:
            lbl = self.font_mono_sm.render(cfg_label, True, ACCENT)
            s.blit(lbl, (r.x + 8, cy))
            cy += 16

            row_rect = pygame.Rect(r.x + 4, cy, r.width - 8, bh + 4)
            pygame.draw.rect(s, BG_DARKER, row_rect)
            pygame.draw.rect(s, BORDER, row_rect, 1)

            btn_dn = pygame.Rect(row_rect.x + 4, cy + 2, bw, bh)
            btn_up = pygame.Rect(row_rect.right - bw - 4, cy + 2, bw, bh)
            self._policy_button_rects[tag_dn] = btn_dn
            self._policy_button_rects[tag_up] = btn_up

            mx, my_ = pygame.mouse.get_pos()
            for btn_rect, tag, blabel in [(btn_dn, tag_dn, "  –  "), (btn_up, tag_up, "  +  ")]:
                hov = btn_rect.collidepoint(mx, my_)
                col = PRIMARY if hov else BORDER
                bg  = (0, 40, 20) if hov else BG_LIGHT
                pygame.draw.rect(s, bg, btn_rect)
                pygame.draw.rect(s, col, btn_rect, 1)
                bt = self.font_mono_med.render(blabel, True, col)
                s.blit(bt, bt.get_rect(center=btn_rect.center))

            val_txt = self.font_mono_med.render(display_val, True, PRIMARY)
            s.blit(val_txt, val_txt.get_rect(centerx=row_rect.centerx, centery=row_rect.centery))

            cy += bh + 14

        pygame.draw.line(s, BORDER, (r.x, cy), (r.right, cy))
        cy += 6

        # ── News wire ──
        wire_lbl = self.font_mono_sm.render("NEWS WIRE", True, SECONDARY)
        s.blit(wire_lbl, (r.x + 8, cy))
        cy += 16

        for ev in self.engine.events[:8]:
            if cy > r.bottom - 14:
                break
            day_str = self.font_mono_sm.render(f"Day {int(ev['time'])}", True, ACCENT)
            s.blit(day_str, (r.x + 8, cy))
            cy += 12

            # Word-wrap event text
            words = ev["text"].split()
            line, lines = "", []
            for w in words:
                test = line + w + " "
                if self.font_mono_sm.size(test)[0] > r.width - 20:
                    lines.append(line)
                    line = w + " "
                else:
                    line = test
            lines.append(line)

            for ln in lines[:2]:
                if cy > r.bottom - 12:
                    break
                t = self.font_mono_sm.render(ln.strip(), True, TEXT_SEC)
                s.blit(t, (r.x + 8, cy))
                cy += 12
            cy += 4

    def _draw_bottom_bar(self, s):
        r = self.bot_rect
        pygame.draw.rect(s, BG_PANEL, r)
        pygame.draw.rect(s, BORDER, r, 1)

        # Draw playback buttons
        for key in ("start", "pause", "spd_dn", "spd_up"):
            self.ctrl_buttons[key].draw(s, self.font_mono_sm)

        # Speed display
        spd = self.font_mono_sm.render(f"SPEED: {self.engine.speed:.1f}x", True, TEXT_PRI)
        s.blit(spd, (self.ctrl_buttons["spd_dn"].rect.x - spd.get_width() - 8,
                     r.y + (r.h - spd.get_height()) // 2))

        # Credits
        cr = self.font_mono_sm.render(
            "Global Macro  |  by Venkatakrishnan Asuri  |  Python port", True, TEXT_SEC
        )
        s.blit(cr, cr.get_rect(centerx=self.WIN_W // 2, centery=r.centery))

    def _draw_tooltip(self, s):
        name = self.tooltip_country
        c = self.engine.countries[name]

        lines = [
            (name,              PRIMARY,   True),
            ("",                TEXT_SEC,  False),
            (f"Growth:  {c['g']:.2f}%",     TEXT_PRI, False),
            (f"Inflation:{c['pi']:.2f}%",    TEXT_PRI, False),
            (f"Debt/GDP:{c['d']:.1f}%",      TEXT_PRI, False),
            (f"Rate:    {c['i']:.2f}%",      TEXT_PRI, False),
            (f"Spread:  {c['rho']:.2f}%",    TEXT_PRI, False),
        ]

        tw = max(self.font_mono_sm.size(l)[0] for l, _, _ in lines if l) + 20
        th = len(lines) * 14 + 10
        tx = min(self.tooltip_pos[0] + 15, self.WIN_W - tw - 5)
        ty = min(self.tooltip_pos[1] + 15, self.WIN_H - th - 5)

        pygame.draw.rect(s, BG_PANEL,  (tx, ty, tw, th))
        pygame.draw.rect(s, PRIMARY,   (tx, ty, tw, th), 1)

        for i, (text, col, bold) in enumerate(lines):
            if text:
                ft = self.font_mono_med if bold else self.font_mono_sm
                t = ft.render(text, True, col)
                s.blit(t, (tx + 8, ty + 5 + i * 14))

    def _draw_gameover(self):
        s = self.screen
        overlay = pygame.Surface((self.WIN_W, self.WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        s.blit(overlay, (0, 0))

        col   = PRIMARY if self.go_win else SECONDARY
        title = "TERM COMPLETE — VICTORY!" if self.go_win else "DISMISSED — GAME OVER"
        t1 = self.font_mono_xl.render(title, True, col)
        t2 = self.font_mono_lg.render(self.go_msg, True, TEXT_PRI)
        t3 = self.font_mono_sm.render("Press any key to continue.", True, TEXT_SEC)

        cx, cy = self.WIN_W // 2, self.WIN_H // 2 - 30
        s.blit(t1, t1.get_rect(centerx=cx, y=cy))
        s.blit(t2, t2.get_rect(centerx=cx, y=cy + 40))
        s.blit(t3, t3.get_rect(centerx=cx, y=cy + 75))
