"""Shared HUD typography, panels, and keyboard-accessible controls."""
import tkinter as tk
from tkinter import ttk

BG = '#050301'
PANEL = '#0c0805'
EDGE = '#5a310f'
CYAN = '#f0a12e'
BLUE = '#c96718'
TEXT = '#f1e2cf'
MUTED = '#a68b6d'
AMBER = '#ff6038'
RED = '#ff4938'
GLOW = '#ffc45c'
DEEP = '#080401'
WARM = '#d8781d'
MONO = ('Consolas', 10)

def label(parent, text='', size=10, color=TEXT, **kwargs):
    return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color, font=('Segoe UI', size), **kwargs)

def button(parent, text, command, accent=False, **kwargs):
    base = '#3a1d08' if accent else '#171009'
    widget = tk.Button(parent, text=text, command=command, bg=base, fg=CYAN if accent else TEXT,
        activebackground='#5a2d0b', activeforeground='#fff5e7', relief='flat', bd=0,
        highlightthickness=1, highlightbackground=EDGE, highlightcolor=CYAN,
        font=('Segoe UI', 9), padx=8, pady=6, cursor='hand2', **kwargs)
    widget._hover_job = None
    def hover(enter):
        if widget._hover_job: widget.after_cancel(widget._hover_job)
        initial = widget.cget('bg')
        target = '#5a2d0b' if enter else base
        def step(frame=1):
            if not widget.winfo_exists(): return
            blend = '#' + ''.join(f'{round(int(initial[i:i+2],16)+(int(target[i:i+2],16)-int(initial[i:i+2],16))*frame/8):02x}' for i in (1,3,5))
            widget.configure(bg=blend, highlightbackground=CYAN if enter else EDGE)
            widget._hover_job = widget.after(16, step, frame+1) if frame < 8 else None
        step()
    widget.bind('<Enter>', lambda _: hover(True))
    widget.bind('<Leave>', lambda _: hover(False))
    widget.bind('<Destroy>', lambda _: widget.after_cancel(widget._hover_job) if widget._hover_job else None, add='+')
    return widget

def panel(parent, title, code='', glow=False, **kwargs):
    frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=GLOW if glow else EDGE, **kwargs)
    # Small machined corner details remain clear at every DPI and resize.
    for anchor,relx,rely in (('nw',0,0),('ne',1,0),('sw',0,1),('se',1,1)):
        corner = tk.Canvas(frame,width=9,height=9,bg=PANEL,highlightthickness=0)
        corner.place(relx=relx,rely=rely,anchor=anchor)
        flip_x,flip_y = anchor.endswith('e'),anchor.startswith('s')
        points = [(0,8),(0,0),(8,0)]
        corner.create_line(*(v for x,y in points for v in (8-x if flip_x else x,8-y if flip_y else y)),
                           fill=GLOW if glow else CYAN,width=1)
    head = tk.Frame(frame, bg=PANEL)
    head.pack(fill='x', padx=12, pady=(9, 7))
    label(head, '▰  ' + title, 9, CYAN).pack(side='left')
    label(head, code, 8, MUTED).pack(side='right')
    frame.sweep = tk.Canvas(frame, bg='#5c310d' if glow else '#3b210c', height=2, highlightthickness=0)
    frame.sweep.pack(fill='x', padx=12)
    frame.sweep_item = frame.sweep.create_line(0, 1, 70, 1, fill=CYAN, width=2)
    body = tk.Frame(frame, bg=PANEL)
    body.pack(fill='both', expand=True, padx=12, pady=(0, 10))
    return frame, body

def configure_ttk(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=PANEL, foreground=TEXT, font=('Segoe UI', 10))
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(10, 7), background=PANEL)
    style.map('TNotebook.Tab', background=[('selected', '#3a210d')], foreground=[('selected', CYAN)])
    style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=29, borderwidth=0)
    style.configure('Treeview.Heading', background='#2d190b', foreground=CYAN, padding=5)
    style.map('Treeview', background=[('selected', '#48270d')])
    style.configure('TCombobox', fieldbackground='#2d190b', foreground=TEXT)
    style.map('TCombobox', fieldbackground=[('readonly', '#2d190b')], foreground=[('readonly', TEXT)], selectbackground=[('readonly', '#2d190b')], selectforeground=[('readonly', TEXT)])

def text_box(parent, **kwargs):
    return tk.Text(parent, bg=PANEL, fg=TEXT, insertbackground=CYAN, selectbackground='#4b2a0d',
                   relief='flat', wrap='word', font=('Segoe UI', 10), padx=3, spacing1=1, spacing3=1, **kwargs)

def set_text(widget, text):
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('end', text)
    widget.configure(state='disabled')
