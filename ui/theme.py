"""Shared HUD typography, panels, and keyboard-accessible controls."""
import tkinter as tk
from tkinter import ttk

BG = '#030811'
PANEL = '#07121e'
EDGE = '#163545'
CYAN = '#34e2e2'
BLUE = '#338de0'
TEXT = '#deedf4'
MUTED = '#829cac'
AMBER = '#f0b45f'
RED = '#f17978'
GLOW = '#57eaff'
DEEP = '#050e1a'
WARM = '#d4943f'
MONO = ('Consolas', 10)

def label(parent, text='', size=10, color=TEXT, **kwargs):
    return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color, font=('Segoe UI', size), **kwargs)

def button(parent, text, command, accent=False, **kwargs):
    base = '#10333e' if accent else '#0b1d2c'
    widget = tk.Button(parent, text=text, command=command, bg=base, fg=CYAN if accent else TEXT,
        activebackground='#174153', activeforeground='#ffffff', relief='flat', bd=0,
        highlightthickness=1, highlightbackground=EDGE, highlightcolor=CYAN,
        font=('Segoe UI', 9), padx=8, pady=6, cursor='hand2', **kwargs)
    widget._hover_job = None
    def hover(enter):
        if widget._hover_job: widget.after_cancel(widget._hover_job)
        initial = widget.cget('bg')
        target = '#174153' if enter else base
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
    head = tk.Frame(frame, bg=PANEL)
    head.pack(fill='x', padx=12, pady=(9, 7))
    label(head, '▰  ' + title, 9, CYAN).pack(side='left')
    label(head, code, 8, MUTED).pack(side='right')
    tk.Frame(frame, bg='#236a7a' if glow else '#1b4351', height=1).pack(fill='x', padx=12)
    body = tk.Frame(frame, bg=PANEL)
    body.pack(fill='both', expand=True, padx=12, pady=(0, 10))
    return frame, body

def configure_ttk(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=PANEL, foreground=TEXT, font=('Segoe UI', 10))
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(10, 7), background=PANEL)
    style.map('TNotebook.Tab', background=[('selected', '#133442')], foreground=[('selected', CYAN)])
    style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=29, borderwidth=0)
    style.configure('Treeview.Heading', background='#102536', foreground=CYAN, padding=5)
    style.map('Treeview', background=[('selected', '#164052')])
    style.configure('TCombobox', fieldbackground='#102536', foreground=TEXT)
    style.map('TCombobox', fieldbackground=[('readonly', '#102536')], foreground=[('readonly', TEXT)], selectbackground=[('readonly', '#102536')], selectforeground=[('readonly', TEXT)])

def text_box(parent, **kwargs):
    return tk.Text(parent, bg=PANEL, fg=TEXT, insertbackground=CYAN, selectbackground='#174153',
                   relief='flat', wrap='word', font=('Segoe UI', 10), padx=3, spacing1=1, spacing3=1, **kwargs)

def set_text(widget, text):
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('end', text)
    widget.configure(state='disabled')
