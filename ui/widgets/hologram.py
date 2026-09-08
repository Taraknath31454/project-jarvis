"""Living holographic AI core: multi-layer projected energy field with smooth
state transitions, particle systems, radial scanner, and holographic shimmer.

Pillow renders rich multi-layer RGBA bloom on resize only.  Each animation frame
repositions existing Canvas items via coords(); no per-frame raster generation.
"""
from dataclasses import dataclass
import math
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk
from ui.theme import PANEL, CYAN, GLOW, MUTED, AMBER, WARM

# ---------------------------------------------------------------------------
# Motion profiles per assistant state
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Motion:
    speed: float
    brightness: float
    expansion: float
    waves: float

PROFILES = {
    'Idle':       Motion(.20, .78, 1.00, .25),
    'Listening':  Motion(.48, .95, 1.08, .75),
    'Processing': Motion(1.60, .98, .95,  .55),
    'Speaking':   Motion(.75, 1.0, 1.12, 1.0),
    'Error':      Motion(.35, .92, 1.04, .85),
    'Offline':    Motion(.06, .35, .96,  .06),
}

def appearance(state: str, mic_active: bool) -> Motion:
    """Microphone-off dims idle only; typed processing/speech stay fully visible."""
    if state == 'Idle' and not mic_active:
        return PROFILES['Offline']
    return PROFILES.get(state, PROFILES['Idle'])

def mix(color: str, strength: float) -> str:
    """Blend *color* with PANEL background.  0 -> pure panel, 1 -> pure color."""
    strength = max(0., min(1., strength))
    return '#' + ''.join(
        f'{int(int(PANEL[i:i+2], 16) * (1 - strength) + int(color[i:i+2], 16) * strength):02x}'
        for i in (1, 3, 5))

# ---------------------------------------------------------------------------
# Smooth interpolation between states
# ---------------------------------------------------------------------------

class SmoothMotion:
    """Mutable motion state that lerps toward target profiles each tick."""
    __slots__ = ('speed', 'brightness', 'expansion', 'waves')

    def __init__(self):
        m = PROFILES['Idle']
        self.speed, self.brightness, self.expansion, self.waves = (
            m.speed, m.brightness, m.expansion, m.waves)

    def approach(self, target, dt, rate=5.0):
        """Move toward *target* Motion; rate controls transition speed."""
        t = min(1.0, dt * rate)
        self.speed       += (target.speed       - self.speed)       * t
        self.brightness  += (target.brightness  - self.brightness)  * t
        self.expansion   += (target.expansion   - self.expansion)   * t
        self.waves       += (target.waves       - self.waves)       * t

# ---------------------------------------------------------------------------
# Main holographic core widget
# ---------------------------------------------------------------------------

class AICore(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=PANEL, highlightthickness=0, width=400, height=100)
        self.phase = self.elapsed = 0.
        self.intensity = .7
        self.state = 'Idle'
        self.radius = 1.
        self.mic_active = False
        self.last_style = None
        self.ready = False
        self.resize_job = None
        self.motion = SmoothMotion()
        self.bind('<Configure>', self.schedule_resize)
        self.bind('<Destroy>', self._destroyed, add='+')
        self.latitude_samples = [i * math.tau / 48 for i in range(49)]
        self.colors = [mix(CYAN, i / 31) for i in range(32)]

    def _destroyed(self, event):
        if event.widget is self and self.resize_job:
            self.after_cancel(self.resize_job)
            self.resize_job = None

    def schedule_resize(self, _=None):
        if self.resize_job:
            self.after_cancel(self.resize_job)
        self.resize_job = self.after(65, self.rebuild)

    # -- Pillow bloom renderer -----------------------------------------------

    def multi_bloom(self, size, color, brightness, warm_center=False):
        """Render rich multi-layer RGBA bloom: atmosphere + halos + luminous core."""
        layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(layer)
        mid   = size / 2
        rgb   = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        warm  = (240, 175, 75)
        _c    = lambda v: max(0, min(255, int(v)))

        # 1. Outer atmospheric haze
        for i in range(38, 0, -1):
            rr = size * (.14 + i * .0085)
            alpha = _c((1 - i/40)**2 * 68 * brightness)
            draw.ellipse((mid-rr, mid-rr, mid+rr, mid+rr), fill=(*rgb, alpha))

        # 2. Mid energy halo ring
        rr_mid = size * .34
        draw.ellipse((mid-rr_mid, mid-rr_mid, mid+rr_mid, mid+rr_mid),
                     outline=(*rgb, _c(110 * brightness)),
                     width=max(2, int(size * .014)))

        # 3. Inner core bloom
        for i in range(26, 0, -1):
            rr = size * (.03 + i * .0065)
            alpha = _c((1 - i/28)**1.4 * 125 * brightness)
            if warm_center and i < 11:
                blend = max(0., 1.0 - i / 9.0)
                cr = int(rgb[0] + (warm[0] - rgb[0]) * blend)
                cg = int(rgb[1] + (warm[1] - rgb[1]) * blend)
                cb = int(rgb[2] + (warm[2] - rgb[2]) * blend)
                draw.ellipse((mid-rr, mid-rr, mid+rr, mid+rr), fill=(cr, cg, cb, alpha))
            else:
                draw.ellipse((mid-rr, mid-rr, mid+rr, mid+rr), fill=(*rgb, alpha))

        # 4. Core glowing ring boundary (clean circular aura)
        rr_core = size * .20
        draw.ellipse((mid-rr_core, mid-rr_core, mid+rr_core, mid+rr_core),
                     outline=(*rgb, _c(175 * brightness)),
                     width=max(2, int(size * .018)))

        # 5. Inner hot nucleus
        for i in range(12, 0, -1):
            rr = size * (.01 + i * .004)
            c_nuc = warm if warm_center else (210, 255, 255)
            draw.ellipse((mid-rr, mid-rr, mid+rr, mid+rr),
                         fill=(*c_nuc, _c((1 - i/14) * 150 * brightness)))

        layer = layer.filter(ImageFilter.GaussianBlur(max(2.5, size / 48)))
        base  = Image.new('RGBA', (size, size), PANEL)
        return ImageTk.PhotoImage(
            Image.alpha_composite(base, layer).convert('RGB'), master=self)

    # -- Canvas rebuild -------------------------------------------------------

    def rebuild(self):
        self.resize_job = None
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20:
            return
        self.cx, self.cy = w / 2, h / 2 - 3
        self.radius = max(25, min(w / 2 - 32, h / 2 - 24))
        r, cx, cy = self.radius, self.cx, self.cy

        # ── Bloom glow (background) ──
        size = max(60, int(r * 2.45))
        self.blooms = {
            'dim':    self.multi_bloom(size, CYAN, .45),
            'normal': self.multi_bloom(size, CYAN, .88),
            'bright': self.multi_bloom(size, GLOW, 1.25, warm_center=True),
            'error':  self.multi_bloom(size, AMBER, 1.05),
        }
        self.glow = self.create_image(cx, cy, image=self.blooms['dim'])

        # ── Static reticle & technical markings ──
        for side in (-1, 1):
            self.create_line(cx + side*r*.95, cy, cx + side*r*1.16, cy,
                             fill='#1e4c5c', width=1)
            self.create_line(cx, cy + side*r*.95, cx, cy + side*r*1.12,
                             fill='#1e4c5c', width=1)

        # 60 Perimeter technical ticks
        for i in range(60):
            a = i * math.tau / 60
            is_major = (i % 5 == 0)
            a_in  = r * (.93 if is_major else .97)
            a_out = r * 1.02
            self.create_line(
                cx + math.cos(a)*a_in,  cy + math.sin(a)*a_in,
                cx + math.cos(a)*a_out, cy + math.sin(a)*a_out,
                fill='#4594a5' if is_major else '#1c4756',
                width=1.5 if is_major else 1)

        for sc in (.95, 1.025):
            rr = r * sc
            self.create_oval(cx-rr, cy-rr, cx+rr, cy+rr, outline='#153543')

        # ── Outer heavy tracking arcs (iconic JARVIS HUD rings) ──
        self.hud_arcs = []
        for i in range(4):
            item = self.create_line(0, 0, 1, 1, fill=CYAN, width=3 if i < 2 else 2)
            self.hud_arcs.append(item)

        # ── Concentric tech ring segments ──
        self.tech_segments = []
        for ri in range(2):
            for seg in range(6):
                item = self.create_line(0, 0, 1, 1, fill=CYAN,
                                        width=2 if ri == 0 else 1)
                self.tech_segments.append((ri, seg, item))

        # ── Energy cage mesh ──
        self.mesh = [self.create_line(0, 0, 1, 1, fill='#277185', width=1)
                     for _ in range(10)]

        # ── Scanner sweep ──
        self.scan_halo = self.create_line(0, 0, 1, 1, fill='#0e2e3e', width=6)
        self.scanner   = self.create_line(0, 0, 1, 1, fill=CYAN,     width=2)

        # ── Orbital ring bands (3D tilted ellipse fragments) ──
        self.rings = []
        for i in range(10):
            self.rings.append(
                self.create_line(0, 0, 1, 1, fill=CYAN,
                                 width=2 if i % 3 == 0 else 1.2))

        # ── Filament arcs (curved energy sweeps) ──
        self.filaments = [self.create_line(0, 0, 1, 1, fill=CYAN, width=1.4)
                          for _ in range(6)]

        # ── Expanding pulse wave rings ──
        self.wave_items = [self.create_oval(0, 0, 1, 1, outline=CYAN, width=1.5)
                           for _ in range(4)]

        # ── Signal rings (audio-reactive expansion) ──
        self.signal_rings = [self.create_oval(0, 0, 1, 1, outline=CYAN, width=1.5)
                             for _ in range(4)]

        # ── Particle field with trails ──
        self.particles = []
        for _ in range(42):
            trail = self.create_line(0, 0, 1, 1, fill='#1b596a', width=1)
            dot   = self.create_oval(0, 0, 2, 2, fill=CYAN, outline='')
            self.particles.append((trail, dot))

        # ── Inner energy sphere & containment rings ──
        self.sphere_fills = [self.create_oval(0, 0, 1, 1, fill=GLOW, outline='')
                             for _ in range(3)]
        self.sphere_rings = [self.create_oval(0, 0, 1, 1, fill='', outline=CYAN,
                                              width=1.5)
                             for _ in range(3)]

        # ── Holographic shimmer sweep beam ──
        self.shimmer = self.create_line(0, 0, 0, 1, fill='', width=2)

        # ── Center seed ──
        self.seed = self.create_oval(0, 0, 1, 1, fill='#d5ffff', outline=GLOW)

        # ── Text overlays ──
        self.monogram = self.create_text(
            cx, cy - r*.02, text='J', fill='#d2ffff',
            font=('Segoe UI Light', max(18, int(r * .20))))
        self.caption = self.create_text(
            cx, cy + r*.23, text='HOLOGRAPHIC CORE', fill=MUTED,
            font=('Consolas', 7))
        self.create_text(5, 8, text='CORE / 02', fill=MUTED,
                         font=('Consolas', 8), anchor='nw')
        self.signal = self.create_text(
            w-5, 8, text='STANDBY', fill=MUTED,
            font=('Consolas', 8), anchor='ne')
        self.create_text(5, h-7, text='LOCAL INTELLIGENCE', fill=MUTED,
                         font=('Consolas', 7), anchor='sw')
        self.create_text(w-5, h-7, text='DETERMINISTIC ENGINE', fill=MUTED,
                         font=('Consolas', 7), anchor='se')

        self.ready, self.last_style = True, None
        self.tick(0, self.state, 0, self.mic_active)

    # -- 3D perspective projection -------------------------------------------

    def project(self, x, y, z, spin=0.):
        """Tilted perspective projection with front/back scale difference."""
        cos, sin = math.cos(spin), math.sin(spin)
        x, z = x*cos + z*sin, z*cos - x*sin
        y, z = y*.90 - z*.435, y*.435 + z*.90
        depth = 1 + z * .13
        return self.cx + x*self.radius*depth, self.cy + y*self.radius*depth

    # -- Per-frame animation tick --------------------------------------------

    def tick(self, dt, state, level=0., mic_active=True):
        self.state, self.mic_active = state, mic_active
        if not self.ready:
            return

        # Smooth interpolation toward target motion state
        target = appearance(state, mic_active)
        self.motion.approach(target, dt)
        m = self.motion

        self.elapsed += dt * self.intensity
        self.phase   += dt * m.speed * self.intensity
        t, p, r = self.elapsed, self.phase, self.radius

        level = max(0., min(1., level))
        beat = ((.5 + .5*math.sin(t*7.2)) if state == 'Speaking'
                else level if state == 'Listening'
                else .5 + .5*math.sin(t*1.6))
        energy    = m.brightness * (.78 + .22*beat)
        expansion = m.expansion + (
            beat*.045 if state in ('Listening', 'Speaking')
            else .008*math.sin(t)) * self.intensity
        hue = AMBER if state == 'Error' else CYAN

        # ── Style swap (on state change only) ──
        style = ('error'  if state == 'Error'
                 else 'dim'    if m.brightness < .45
                 else 'bright' if state in ('Listening', 'Processing', 'Speaking')
                 else 'normal')
        if self.last_style != (style, state, mic_active):
            self.itemconfigure(self.glow, image=self.blooms[style])
            sig = (state.upper() if state != 'Idle'
                   else 'RECEPTIVE' if mic_active else 'MIC OFF / STANDBY')
            self.itemconfigure(self.signal, text=sig,
                               fill=AMBER if state == 'Error' else MUTED)
            self.itemconfigure(self.monogram,
                               fill='#ffe1b0' if state == 'Error' else '#d2ffff')
            self.last_style = (style, state, mic_active)

        # ── Heavy outer HUD tracking arcs ──
        for i, item in enumerate(self.hud_arcs):
            sc = (.84 + (i%2)*.08) * expansion
            rot = p * (.22 if i%2 == 0 else -.18) + i * math.pi/2
            span = math.pi * (.35 if i < 2 else .25)
            pts = []
            for j in range(12):
                a = rot + j * span / 11
                pts.extend((self.cx + math.cos(a)*r*sc,
                            self.cy + math.sin(a)*r*sc*.94))
            self.coords(item, *pts)
            arc_brt = energy * (.55 + .35*math.sin(t*.9 + i))
            self.itemconfigure(item, fill=mix(hue, arc_brt))

        # ── Tech ring segments ──
        for ri, seg, item in self.tech_segments:
            sc = (1.04 + ri*.08) * expansion
            rot = p * (.12 if ri == 0 else -.09)
            ba = rot + seg * math.tau / 6
            span = math.tau / 6 * .60
            pts = []
            for j in range(7):
                a = ba + j * span / 6
                pts.extend((self.cx + math.cos(a)*r*sc,
                            self.cy + math.sin(a)*r*sc*.93))
            self.coords(item, *pts)
            self.itemconfigure(
                item, fill=mix(hue, energy*(.28 + ri*.08 +
                                            .08*math.sin(t*.7 + seg))))

        # ── Energy cage mesh ──
        for i, item in enumerate(self.mesh):
            pts = []
            shim = .08 * math.sin(t*1.1 + i*2.3)
            for a in self.latitude_samples:
                if i < 5:
                    lat = (i - 2) * .22
                    rr = (math.sqrt(max(0, .48**2 - lat**2))
                          if abs(lat) < .48 else .10)
                    x, y, z = math.cos(a)*rr, lat*.7, math.sin(a)*rr
                else:
                    ang = (i - 5) * math.pi / 5
                    x = math.cos(a)*math.cos(ang)*.48
                    y = math.sin(a)*.48
                    z = math.cos(a)*math.sin(ang)*.48
                pts.extend(self.project(
                    x*expansion, y*expansion, z*expansion, p*.45))
            self.coords(item, *pts)
            self.itemconfigure(
                item, fill=mix('#53ddec', energy*(.30 + .04*(i%4) + shim)))

        # ── Scanner sweep (radial arc) ──
        spd = 3.0 if state == 'Processing' else .60
        sa  = t * spd
        al  = .35 if state == 'Processing' else .20
        s_pts, h_pts = [], []
        for j in range(10):
            a  = sa - j * al / 9
            sr = r * (.91 + .015*math.sin(a*3))
            s_pts.extend((self.cx + math.cos(a)*sr,
                          self.cy + math.sin(a)*sr*.92))
            hr = sr * 1.02
            h_pts.extend((self.cx + math.cos(a)*hr,
                          self.cy + math.sin(a)*hr*.92))
        self.coords(self.scanner,   *s_pts)
        self.coords(self.scan_halo, *h_pts)
        self.itemconfigure(
            self.scanner, fill=mix(hue, energy*(.88 if state == 'Processing'
                                                else .30)))
        self.itemconfigure(
            self.scan_halo, fill=mix(hue, energy*(.25 if state == 'Processing'
                                                  else .08)))

        # ── Orbital ring bands ──
        for i, item in enumerate(self.rings):
            sc    = (.68 + i*.032) * expansion
            start = p * (1 if i%2 else -1) * (1 + i*.10) + i*.75
            pts   = []
            for j in range(25):
                a = start + j*.038*(1 + i%3*.45)
                pts.extend(self.project(
                    math.cos(a)*sc,
                    math.sin(a)*sc*(.48 + i*.042),
                    math.sin(a)*sc*.40,
                    .20*math.sin(p*.4 + i)))
            self.coords(item, *pts)
            self.itemconfigure(item, fill=mix(hue, energy*(.45 + .05*i)))

        # ── Filament arcs ──
        for i, item in enumerate(self.filaments):
            pts   = []
            n_pts = 42
            for j in range(n_pts):
                a  = j * math.tau / max(1, n_pts - 1)
                rr = (.25 + .055*math.sin(a*3 + t*1.4 + i)
                          + .035*math.sin(a*7 - t*.7)) * expansion
                pts.extend(self.project(
                    math.cos(a + i)*rr, math.sin(a)*rr,
                    math.sin(a*2 + p + i)*.19, p*.7 + i))
            if len(pts) >= 4:
                self.coords(item, *pts)
            brt = energy * (.62 + i*.06)
            self.itemconfigure(item, fill=mix(GLOW if i%2 else hue, brt))

        # ── Expanding wave rings ──
        for i, item in enumerate(self.wave_items):
            cycle = (t*(.28 + m.waves*.42) + i/4) % 1
            rr = r * (.38 + cycle*.68) * expansion
            self.coords(item, self.cx-rr, self.cy-rr*.90,
                              self.cx+rr, self.cy+rr*.90)
            self.itemconfigure(
                item, outline=mix(hue, (1-cycle)*m.waves*energy*.60))

        # ── Signal rings (active during Speaking / Listening) ──
        for i, item in enumerate(self.signal_rings):
            active = state in ('Speaking', 'Listening')
            if active:
                sp    = .52 if state == 'Speaking' else .30
                cycle = (t*sp + i/4) % 1
                rr    = r * (.18 + cycle*.90) * expansion
                alpha = (1-cycle) * m.waves * energy * .48
            else:
                rr, alpha = r*.01, 0
            self.coords(item, self.cx-rr, self.cy-rr*.90,
                              self.cx+rr, self.cy+rr*.90)
            self.itemconfigure(item, outline=mix(hue, alpha))

        # ── Particles with trails ──
        for i, (trail, dot) in enumerate(self.particles):
            a     = (i*2.399963
                     + p*(.22 + (i%7)*.06)*(-1 if i%2 else 1))
            orbit = (.50 + (i%11)*.038) * expansion
            z     = math.sin(a + i) * .28
            x, y   = self.project(math.cos(a)*orbit,
                                  math.sin(a)*orbit*.78, z,
                                  .12*math.sin(p))
            xx, yy = self.project(math.cos(a-.09)*orbit,
                                  math.sin(a-.09)*orbit*.78, z,
                                  .12*math.sin(p))
            sz = (.60 + (i%3)*.30) * (1 + max(z, 0))
            self.coords(dot, x-sz, y-sz, x+sz, y+sz)
            self.coords(trail, xx, yy, x, y)
            self.itemconfigure(dot,   fill=mix(hue, energy*(.48 + (i%5)*.11)))
            self.itemconfigure(trail, fill=mix(hue, energy*.28))

        # ── Inner energy sphere & containment rings ──
        for i, item in enumerate(self.sphere_fills):
            ang = t*(.5 + i*.22) + i*math.tau/3
            ox  = math.sin(ang) * r * .016
            oy  = math.cos(ang*1.3) * r * .012
            rr  = r * (.035 + .012*math.sin(t*1.2 + i))
            sx, sy = self.cx + ox, self.cy + oy
            self.coords(item, sx-rr, sy-rr, sx+rr, sy+rr)
            col = WARM if i == 0 and state != 'Error' else GLOW
            self.itemconfigure(
                item, fill=mix(col, energy*(.60 + .25*math.sin(t + i))))

        for i, item in enumerate(self.sphere_rings):
            ang = t*(.35 + i*.15) + i*math.tau/3
            ox  = math.sin(ang) * r * .020
            oy  = math.cos(ang*1.1) * r * .016
            rr  = r * (.07 + i*.030 + .014*math.sin(t*.9 + i*1.5))
            sx, sy = self.cx + ox, self.cy + oy
            self.coords(item, sx-rr, sy-rr*.94, sx+rr, sy+rr*.94)
            self.itemconfigure(
                item, outline=mix(hue, energy*(.38 + .12*math.sin(t*1.3 + i))))

        # ── Holographic shimmer sweep line ──
        period = 4.2
        cycle  = (t / period) % 1
        sx     = self.cx - r*1.15 + cycle*r*2.3
        sa     = math.sin(cycle*math.pi)**2 * .35 * energy
        self.coords(self.shimmer,
                    sx - r*.12, self.cy - r*.85,
                    sx + r*.12, self.cy + r*.85)
        self.itemconfigure(self.shimmer, fill=mix(GLOW, sa))

        # ── Center seed ──
        rr = r * (.024 + .006*beat)
        self.coords(self.seed,
                    self.cx-rr, self.cy + r*.30 - rr,
                    self.cx+rr, self.cy + r*.30 + rr)
