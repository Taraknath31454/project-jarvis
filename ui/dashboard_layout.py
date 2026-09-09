"""Responsive three-column HUD layout; all actions delegate to Desktop.submit."""
import tkinter as tk
from ui.theme import BG, PANEL, EDGE, CYAN, GLOW, TEXT, MUTED, DEEP, label, button, panel, text_box
from ui.widgets.ai_core import AICore, Waveform
from ui.widgets.telemetry import Gauge, PerformanceGraph

def build(d):
    root = d.root
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(1, weight=1)
    sidebar = tk.Frame(root, bg='#090603', width=86, highlightbackground=EDGE, highlightthickness=1)
    sidebar.grid(row=0, column=0, rowspan=5, sticky='nsew', padx=(10, 0), pady=10)
    sidebar.grid_propagate(False)
    label(sidebar, 'J', 28, GLOW, justify='center').pack(fill='x', pady=(14, 0))
    label(sidebar, 'C O R E', 7, MUTED).pack(fill='x', pady=(0, 20))
    nav = [
        ('HOME', d.focus_input),
        ('COMMANDS', lambda: d.palette(True)),
        ('APPS', lambda: (d.entry.delete(0, 'end'), d.entry.insert(0, 'open '), d.entry.focus_set())),
        ('FILES', lambda: d.submit('open File Explorer')),
        ('NOTES', d.notes),
        ('REMINDERS', d.reminders_window),
        ('SYSTEM', lambda: d.submit('system status')),
        ('SETTINGS', d.settings),
    ]
    d.nav_buttons = []
    for caption, action in nav:
        item = button(sidebar, caption, action)
        item.configure(font=('Segoe UI', 7), padx=2, pady=8)
        item.pack(fill='x', padx=7, pady=2)
        d.nav_buttons.append(item)
    label(sidebar, 'V2', 7, MUTED).pack(side='bottom', pady=12)
    header = tk.Frame(root, bg=BG)
    header.grid(row=0, column=1, sticky='ew', padx=12, pady=(10, 8))
    label(header, 'J A R V I S', 24, CYAN).pack(side='left')
    subtitle = label(header, 'HOLOGRAPHIC INTERFACE\nPERSONAL AI / V2', 8, MUTED, justify='left')
    subtitle.pack(side='left', padx=16)
    d.header_status = label(header, '● SYSTEM ONLINE\nLOCAL MODE', 9, CYAN, justify='left')
    d.header_status.pack(side='left', padx=8)
    motto = label(header, 'L I S T E N   •   T H I N K   •   A C T', 8, CYAN)
    motto.pack(side='left', expand=True)
    for caption, action in [('×', d.request_close), ('□', d.maximize), ('—', d.hide), ('SETTINGS', d.settings), ('COMMANDS', lambda: d.palette(True))]:
        button(header, caption, action).pack(side='right', padx=3)
    d.clock_label = label(header, '', 10, TEXT, justify='right')
    d.clock_label.pack(side='right', padx=14)
    dashboard = tk.Frame(root, bg=BG)
    dashboard.grid(row=1, column=1, sticky='nsew', padx=12)
    dashboard.columnconfigure(0, weight=1, minsize=235)
    dashboard.columnconfigure(1, weight=7, minsize=330)
    dashboard.columnconfigure(2, weight=1, minsize=270)
    dashboard.rowconfigure(0, weight=1)
    d.dashboard = dashboard
    frame, left = panel(dashboard, 'SYSTEM TELEMETRY', '01')
    d.left_panel = frame
    frame.configure(width=260)
    frame.pack_propagate(False)
    frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
    gauges = tk.Frame(left, bg=PANEL)
    gauges.pack(fill='x')
    gauges.columnconfigure((0, 1), weight=1)
    d.gauges = {}
    for i, key in enumerate(('cpu', 'ram', 'battery', 'storage')):
        gauge = Gauge(gauges, key.upper())
        gauge.grid(row=i//2, column=i%2, sticky='ew', pady=1)
        d.gauges[key] = gauge
    d.hardware_label = label(left, 'GPU N/A • BATTERY N/A\nPROCESSES N/A • UPTIME N/A', 8, MUTED, justify='left', anchor='w')
    d.hardware_label.pack(fill='x', pady=(2, 4))
    d.device_label = label(left, 'DEVICE / CONNECTING…', 8, TEXT, anchor='w')
    d.device_label.pack(fill='x')
    tk.Frame(left, bg=EDGE, height=1).pack(fill='x', pady=5)
    d.network_label = label(left, 'INTERNET N/A • WI-FI N/A\n↓ N/A   ↑ N/A', 8, CYAN, justify='left', anchor='w')
    d.network_label.pack(fill='x')
    modes = tk.Frame(left, bg=PANEL)
    modes.pack(fill='x', pady=(4, 2))
    d.graph = PerformanceGraph(left)
    for mode in ('CPU', 'RAM', 'Network'):
        button(modes, mode.upper(), lambda m=mode: d.graph.set_mode(m)).pack(side='left', expand=True, fill='x', padx=1)
    d.graph.pack(fill='both', expand=True)
    frame, center = panel(dashboard, 'JARVIS / AI CORE', 'LOCAL / SECURE', glow=True)
    d.core_panel = frame
    frame.grid(row=0, column=1, sticky='nsew', padx=(0, 10))
    d.core = AICore(center)
    d.core.pack(fill='both', expand=True)
    core_status = tk.Frame(center, bg=PANEL)
    core_status.pack(fill='x', pady=3)
    label(core_status, 'J A R V I S', 12, TEXT).pack(side='left', expand=True, anchor='e', padx=(0, 8))
    d.state_label = tk.Label(core_status, text='IDLE', fg=CYAN, bg=PANEL, font=('Consolas', 11, 'bold'))
    d.state_label.pack(side='left', expand=True, anchor='w', padx=(8, 0))
    d.waveform = Waveform(center)
    d.waveform.pack(fill='x')
    mic_row = tk.Frame(center, bg=PANEL)
    mic_row.pack(pady=(3, 2))
    d.mic_indicator = tk.Label(mic_row, textvariable=d.mic_label, fg=MUTED, bg=PANEL, font=('Consolas', 8))
    d.mic_indicator.pack(side='left', padx=(0, 12))
    d.mic_button = button(mic_row, '◉ ENABLE MICROPHONE', d.toggle_mic, True)
    d.mic_button.pack(side='left')
    label(center, 'VOICE / LOCAL RECOGNITION / NO AUDIO UPLOAD', 7, MUTED).pack(pady=(3, 0))
    frame, right = panel(dashboard, 'QUICK LAUNCH', 'CONTROL')
    d.right_panel = frame
    frame.configure(width=290)
    frame.pack_propagate(False)
    frame.grid(row=0, column=2, sticky='nsew')
    quick = tk.Frame(right, bg=PANEL)
    quick.pack(fill='x')
    quick.columnconfigure((0, 1, 2), weight=1)
    for i, app in enumerate(d.config['dashboard']['quick_launch']):
        caption = {'File Explorer': 'EXPLORER', 'Settings': 'WINDOWS'}.get(app, app.upper())
        button(quick, caption, lambda name=app: d.submit('open '+name)).grid(row=i//3, column=i%3, sticky='ew', padx=2, pady=2)
    tk.Frame(right, bg=EDGE, height=1).pack(fill='x', pady=8)
    d.weather_label = label(right, 'WEATHER / OPTIONAL\nConfigure location in Settings', 9, MUTED, justify='left', anchor='w')
    d.weather_label.pack(fill='x')
    tk.Frame(right, bg=EDGE, height=1).pack(fill='x', pady=8)
    row = tk.Frame(right, bg=PANEL)
    row.pack(fill='x')
    label(row, 'UPCOMING', 9, CYAN).pack(side='left')
    button(row, 'VIEW ALL', d.reminders_window).pack(side='right')
    d.reminder_label = label(right, 'No pending reminders.', 9, MUTED, justify='left', anchor='nw')
    d.reminder_label.pack(fill='both', expand=True, pady=(4, 2))
    notes = tk.Frame(right, bg=PANEL)
    notes.pack(fill='x', pady=(3, 4))
    button(notes, '+ NEW NOTE', d.new_note).pack(side='left', expand=True, fill='x', padx=(0, 3))
    button(notes, 'VIEW NOTES', d.notes).pack(side='left', expand=True, fill='x', padx=(3, 0))
    tk.Frame(right, bg=EDGE, height=1).pack(fill='x', pady=5)
    d.media_label = label(right, 'MEDIA / No active session', 8, MUTED, anchor='w')
    d.media_label.pack(fill='x', pady=(0, 4))
    media = tk.Frame(right, bg=PANEL)
    d.media_controls = media
    media.pack(fill='x')
    for caption, command in [('⏮', 'previous song'), ('▶ / Ⅱ', 'toggle music'), ('⏭', 'next song'), ('−', 'decrease volume'), ('MUTE', 'mute'), ('+', 'increase volume')]:
        button(media, caption, lambda c=command: d.submit(c)).pack(side='left', fill='x', expand=True, padx=1)
    lower = tk.Frame(root, bg=BG)
    lower.grid(row=2, column=1, sticky='ew', padx=12, pady=(9, 7))
    lower.columnconfigure(0, weight=5)
    lower.columnconfigure(1, weight=2)
    lower.columnconfigure(2, weight=2)
    frame, body = panel(lower, 'LIVE TRANSCRIPT', 'MEMORY ONLY')
    d.transcript_panel = frame
    frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
    d.output = text_box(body, height=3, width=40)
    d.output.pack(fill='both', expand=True)
    d.output.configure(state='disabled')
    d.output.tag_configure('speaker', foreground=CYAN, font=('Consolas', 10, 'bold'))
    d.output.tag_configure('you', foreground=MUTED, font=('Consolas', 9))
    d.output.configure(spacing1=1, spacing3=2)
    frame, body = panel(lower, 'RECENT ACTIVITY', 'LOCAL')
    frame.grid(row=0, column=1, sticky='nsew', padx=(0, 10))
    d.history = text_box(body, height=3, width=24)
    d.history.pack(fill='both', expand=True)
    d.history.configure(state='disabled')
    frame, body = panel(lower, 'NOTIFICATIONS', '●')
    frame.grid(row=0, column=2, sticky='nsew')
    d.notification_label = label(body, '', 8, MUTED, justify='left', anchor='nw', wraplength=230)
    d.notification_label.pack(fill='both', expand=True)
    terminal = tk.Frame(root, bg=DEEP, highlightbackground=EDGE, highlightthickness=1)
    d.terminal = terminal
    terminal.grid(row=3, column=1, sticky='ew', padx=12)
    label(terminal, ' > ', 18, CYAN).pack(side='left', padx=(8, 0))
    d.voice_caption = tk.Label(terminal, textvariable=d.voice_prompt, bg=DEEP, fg=CYAN,
                               font=('Consolas', 8, 'bold'), width=25, anchor='w')
    d.voice_caption.pack(side='left', padx=(2, 8))
    d.entry = tk.Entry(terminal, bg=DEEP, fg=TEXT, insertbackground=CYAN, relief='flat', font=('Consolas', 12))
    d.entry.pack(side='left', fill='x', expand=True, ipady=11, padx=8)
    d.entry.bind('<Return>', lambda _: d.submit())
    d.entry.bind('<FocusIn>', lambda _: terminal.configure(highlightbackground=GLOW))
    d.entry.bind('<FocusOut>', lambda _: terminal.configure(highlightbackground=EDGE))
    button(terminal, 'CLEAR HISTORY', d.clear_history).pack(side='right', padx=7)
    button(terminal, 'SEND ↵', d.submit, True).pack(side='right', padx=5)
    footer = tk.Frame(root, bg=BG)
    footer.grid(row=4, column=1, sticky='ew', padx=12, pady=(5, 6))
    label(footer, '● LOCAL FIRST', 8, CYAN).pack(side='left')
    label(footer, 'CTRL+SPACE  INPUT    CTRL+K  PALETTE    F11  FULLSCREEN', 8, MUTED).pack(side='left', padx=18)
    button(footer, 'SCREENSHOTS ↗', lambda: d.submit('open screenshots')).pack(side='right')
    d.entry.focus_set()
    # Preserve a readable graph and all controls at the supported minimum height.
    d.compact_layout = None
    separators = [(child, child.pack_info()['pady']) for child in right.winfo_children()
                  if isinstance(child, tk.Frame) and int(child.cget('height')) == 1]
    def adapt():
        compact = root.winfo_height() < 700
        narrow = root.winfo_width() < 1250
        if (compact,narrow) == d.compact_layout:
            return
        d.compact_layout = (compact,narrow)
        if narrow:
            motto.pack_forget()
            subtitle.pack_forget()
        else:
            subtitle.pack(side='left', padx=16, before=d.header_status)
            motto.pack(side='left', expand=True, after=d.header_status)
        for gauge in d.gauges.values():
            gauge.configure(height=62 if compact else 82)
        d.output.configure(height=2 if compact else 3)
        d.history.configure(height=2 if compact else 3)
        for separator, padding in separators:
            separator.pack_configure(pady=2 if compact else padding)
    d.adapt_layout = adapt
