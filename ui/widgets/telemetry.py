import tkinter as tk
from collections import deque
from ui.theme import PANEL, EDGE, CYAN, BLUE, TEXT, MUTED

def rate(value):
    if value is None: return 'N/A'
    if value >= 1024*1024: return f'{value/1024/1024:.1f} MB/s'
    return f'{value/1024:.1f} KB/s'

class Gauge(tk.Canvas):
    def __init__(self, parent, name):
        super().__init__(parent, bg=PANEL, height=82, width=100, highlightthickness=0)
        self.name, self.value, self.display = name, None, 0
        self.last_value = object()
        self.bind('<Configure>', self.draw)

    def draw(self, _=None):
        self.delete('all')
        self.last_value = object()
        w, h = self.winfo_width(), self.winfo_height()
        r, cx, cy = min(w/2-10, h/2-12), w/2, h/2-5
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=225, extent=-270, style='arc', outline=EDGE, width=5)
        self.arc = self.create_arc(cx-r, cy-r, cx+r, cy+r, start=225, extent=0, style='arc', outline=CYAN, width=5)
        self.number = self.create_text(cx, cy-2, text='N/A', fill=TEXT, font=('Consolas', 15, 'bold'))
        self.create_text(cx, cy+r+7, text=self.name, fill=MUTED, font=('Consolas', 8))

    def tick(self):
        if not hasattr(self, 'arc'): return
        if self.last_value == self.value and (self.value is None or abs(self.value-self.display) < .05):
            return
        if self.value is not None:
            self.display += (self.value-self.display)*.18
        self.itemconfigure(self.arc, extent=-270*self.display/100 if self.value is not None else 0)
        if self.last_value != self.value:
            self.itemconfigure(self.number, text=f'{self.value:.0f}%' if self.value is not None else 'N/A')
        self.last_value = self.value

class PerformanceGraph(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, height=70, width=220, bg=PANEL, highlightthickness=0)
        self.samples = deque(maxlen=60)
        self.mode = 'CPU'
        self.bind('<Configure>', lambda _: self.draw())

    def add(self, sample):
        self.samples.append(sample)
        self.draw()

    def set_mode(self, value):
        self.mode = value
        self.draw()

    def draw(self):
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        for i in range(1, 4):
            self.create_line(0, i*h/4, w, i*h/4, fill=EDGE)
        keys = ['download', 'upload'] if self.mode == 'Network' else [self.mode.lower()]
        maximum = max([s[k] or 0 for s in self.samples for k in keys] + [1024]) if self.mode == 'Network' else 100
        for key, color in zip(keys, (CYAN, BLUE)):
            segment = []
            for i, sample in enumerate(self.samples):
                value = sample.get(key)
                if value is None:
                    if len(segment) >= 4: self.create_line(*segment, fill=color, width=1.5)
                    segment = []
                    continue
                segment.extend((w*i/59, h-5 - min(1, value/maximum)*(h-16)))
            if len(segment) >= 4: self.create_line(*segment, fill=color, width=1.5)
        caption = f'{rate(maximum)} peak • ↓ gold / ↑ ember' if self.mode == 'Network' else '0—100%  /  last 60 samples'
        self.create_text(3, 2, text=caption, fill=MUTED, anchor='nw', font=('Consolas', 7))
