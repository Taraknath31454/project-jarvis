"""Voice waveform plus the hologram renderer re-export."""
import math
import tkinter as tk
from ui.theme import PANEL, CYAN
from ui.widgets.hologram import AICore


class Waveform(tk.Canvas):
    """Audio-reactive bar waveform with center emphasis and glowing baseline."""

    def __init__(self, parent):
        super().__init__(parent, height=26, width=180, bg=PANEL, highlightthickness=0)
        self.phase = 0
        self.last_frame = None
        self.baseline = self.create_line(0, 0, 0, 0, fill='#152d3c', width=1)
        self.bars = [self.create_line(0, 0, 0, 0, fill=CYAN, width=2)
                     for _ in range(48)]

    def tick(self, state, level, dt):
        self.phase += dt * 8
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
        self.itemconfigure(self.baseline, fill='#1e4558' if active else '#152d3c')

        for i, item in enumerate(self.bars):
            # Center emphasis: bars near center are taller
            center_w = 1 - abs(i - n / 2) / (n / 2) * .4
            wave = abs(math.sin(self.phase + i * .55)
                       * math.sin(i * .35 + self.phase * .7))

            if state == 'Speaking':
                amount = .50 * center_w + .25 * (
                    .5 + .5 * math.sin(self.phase * 1.4 + i * .3))
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
                r = int(0x07 + (0x34 - 0x07) * brt)
                g = int(0x12 + (0xe2 - 0x12) * brt)
                b = int(0x1e + (0xe2 - 0x1e) * brt)
                self.itemconfigure(item, fill=f'#{r:02x}{g:02x}{b:02x}')
            else:
                self.itemconfigure(item, fill='#1e4558')
