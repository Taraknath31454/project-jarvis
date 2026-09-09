"""Voice waveform plus the hologram renderer re-export."""
import math
import tkinter as tk
from ui.theme import PANEL, CYAN
from ui.widgets.hologram import AICore, voice_envelope, mix


class Waveform(tk.Canvas):
    """Audio-reactive bar waveform with center emphasis and glowing baseline."""

    def __init__(self, parent):
        super().__init__(parent, height=26, width=180, bg=PANEL, highlightthickness=0)
        self.phase = 0
        self.last_frame = None
        self.baseline = self.create_line(0, 0, 0, 0, fill=mix(CYAN, .16), width=1)
        self.bars = [self.create_line(0, 0, 0, 0, fill=CYAN, width=2)
                     for _ in range(48)]

    def tick(self, state, level, dt, elapsed=None):
        self.phase = self.phase + dt if elapsed is None else elapsed
        signature = (state, self.winfo_width())
        if state not in ('Listening', 'Speaking') and signature == self.last_frame:
            return
        self.last_frame = signature
        w = self.winfo_width()
        h = self.winfo_height()
        mid_y = h / 2
        width = min(w - 10, 280)
        start = (w - width) / 2
        n = len(self.bars)

        # Glowing baseline
        self.coords(self.baseline, start, mid_y, start + width, mid_y)
        active = state in ('Listening', 'Speaking')
        self.itemconfigure(self.baseline, fill=mix(CYAN, .35 if active else .16))

        for i, item in enumerate(self.bars):
            # Center emphasis: bars near center are taller
            center_w = 1 - abs(i - n / 2) / (n / 2) * .4
            wave = abs(math.sin(self.phase * 8 + i * .55)
                       * math.sin(i * .35 + self.phase * 5.6))

            if state == 'Speaking':
                amount = (.12 + .88 * voice_envelope(self.phase)) * center_w
            elif state == 'Listening':
                amount = level * center_w
            else:
                amount = .03

            height = 1 + wave * 14 * amount
            x = start + i * width / max(1, n - 1)
            self.coords(item, x, mid_y - height, x, mid_y + height)

            if active:
                # Brighter at center
                brt = .55 + .45 * center_w
                self.itemconfigure(item, fill=mix(CYAN, brt))
            else:
                self.itemconfigure(item, fill=mix(CYAN, .18))
