"""Sectioned settings over the existing JSON schema, with atomic validated saves."""
import copy
import json
import tkinter as tk
from tkinter import messagebox
from core.config import validate, save_config
from services.desktop_integration import Startup
from ui.theme import BG, PANEL, CYAN, TEXT, MUTED, EDGE, label, button, text_box

# path, label, input type. Mapping editors are confined to alias settings.
SECTIONS = {
    'GENERAL': [('assistant_name', 'Assistant name', str), ('user_name', 'User name', str),
                ('desktop.start_with_windows', 'Start with Windows (current user)', bool),
                ('desktop.start_minimized', 'Start minimized', bool), ('desktop.startup_greeting', 'Speak startup greeting', bool),
                ('desktop.startup_sound', 'Play a short startup tone', bool)],
    'VOICE': [('tts.enabled', 'Spoken responses', bool), ('tts.voice_id', 'Windows voice ID (blank = default)', str),
              ('tts.rate', 'Speech rate • 50–400', int), ('tts.volume', 'Speech volume • 0–1', float),
              ('microphone.device', 'Input device index (blank = default)', 'optional_int'),
              ('microphone.wake_word', 'Wake word', str), ('microphone.follow_up_seconds', 'Follow-up window • seconds', float),
              ('microphone.model_path', 'Offline model folder', str)],
    'APPLICATIONS': [('chrome_executable', 'Chrome executable (blank = discover)', str),
                     ('app_paths', 'Executable paths • JSON name-to-path mapping', dict),
                     ('app_aliases', 'Spoken aliases • JSON alias-to-app mapping', dict),
                     ('dashboard.quick_launch', 'Quick launch names • JSON list, up to 12', list)],
    'CHROME PROFILES': [('chrome_profiles', 'JSON spoken-name → directory mapping (e.g. Profile 1)', dict)],
    'FOLDERS': [('folder_aliases', 'Folder aliases • JSON name-to-path mapping', dict),
                ('search.roots', 'Search folders • JSON list', list)],
    'WEBSITES': [('website_aliases', 'Website aliases • JSON name-to-HTTPS-URL mapping', dict)],
    'SYSTEM': [('desktop.tray_enabled', 'Enable system tray', bool), ('desktop.close_to_tray', 'Close window to tray', bool),
               ('desktop.global_hotkey_enabled', 'Enable global focus hotkey', bool),
               ('desktop.global_hotkey', 'Global hotkey • Ctrl+Alt+letter', str),
               ('monitor.interval_seconds', 'Telemetry interval • 1–30 seconds', float),
               ('monitor.low_battery_warning', 'Low battery notification', bool),
               ('monitor.low_battery_percent', 'Low battery threshold • 5–50 percent', int),
               ('safety.allow_power_commands', 'Enable shutdown/restart (still requires confirmation)', bool)],
    'APPEARANCE': [('dashboard.animation_intensity', 'Animation intensity • 0–1 (0 = still)', float),
                   ('dashboard.fps', 'Animation frame limit • 10–60', int), ('dashboard.fullscreen', 'Start fullscreen', bool)],
    'WEATHER': [('weather.enabled', 'Enable Open-Meteo weather', bool), ('weather.city', 'City display name', str),
                ('weather.latitude', 'Latitude • -90 to 90', 'optional_float'),
                ('weather.longitude', 'Longitude • -180 to 180', 'optional_float'),
                ('weather.refresh_minutes', 'Refresh interval • 5–120 minutes', int)],
    'PRIVACY': [('privacy.transcript_enabled', 'Keep recent interactions in memory only', bool),
                ('privacy.transcript_limit', 'Maximum in-memory interactions • 1–30', int)],
}

def get_value(config, path):
    value = config
    for key in path.split('.'): value = value[key]
    return value

def set_value(config, path, value):
    keys = path.split('.')
    target = config
    for key in keys[:-1]: target = target[key]
    target[keys[-1]] = value

class SettingsWindow:
    def __init__(self, desktop):
        self.desktop = desktop
        self.config = copy.deepcopy(desktop.assistant.config)
        self.window = tk.Toplevel(desktop.root)
        self.window.title('JARVIS • System configuration')
        self.window.geometry('880x650')
        self.window.minsize(700, 480)
        self.window.configure(bg=BG)
        self.values, self.panels = {}, {}
        label(self.window, 'SYSTEM CONFIGURATION', 15, CYAN).pack(anchor='w', padx=22, pady=(18, 4))
        label(self.window, 'Changes are validated before saving. Restart JARVIS to apply runtime settings.', 10, MUTED).pack(anchor='w', padx=22, pady=(0, 12))
        self.body = tk.Frame(self.window, bg=BG)
        self.body.pack(fill='both', expand=True, padx=20)
        nav = tk.Listbox(self.body, bg=PANEL, fg=MUTED, selectbackground='#163947', selectforeground=CYAN,
                         width=20, relief='flat', bd=0, font=('Consolas', 11), activestyle='none', exportselection=False)
        nav.pack(side='left', fill='y', padx=(0, 14))
        host = tk.Frame(self.body, bg=PANEL)
        host.pack(fill='both', expand=True)
        for section, descriptors in SECTIONS.items():
            nav.insert('end', section)
            frame = tk.Frame(host, bg=PANEL)
            canvas = tk.Canvas(frame, bg=PANEL, highlightthickness=0)
            scroll = tk.Scrollbar(frame, command=canvas.yview)
            scroll.pack(side='right', fill='y')
            canvas.pack(fill='both', expand=True)
            canvas.configure(yscrollcommand=scroll.set)
            form = tk.Frame(canvas, bg=PANEL, padx=16, pady=14)
            item = canvas.create_window(0, 0, anchor='nw', window=form)
            canvas.bind('<Configure>', lambda event, c=canvas, i=item: c.itemconfigure(i, width=event.width))
            form.bind('<Configure>', lambda _, c=canvas: c.configure(scrollregion=c.bbox('all')))
            label(form, section, 12, CYAN).pack(anchor='w', pady=(0, 14))
            if section == 'WEATHER':
                label(form, 'Optional. Configured coordinates are sent to Open-Meteo when enabled.\nNo API key is required. Attribution: open-meteo.com', 9, MUTED, justify='left').pack(anchor='w', pady=(0, 12))
            if section == 'PRIVACY':
                label(form, 'Audio is never recorded to disk or uploaded. Activity logs omit payloads.\nNotes and reminders remain in your existing local database.', 9, MUTED, justify='left').pack(anchor='w', pady=(0, 12))
            for path, caption, kind in descriptors:
                value = get_value(self.config, path)
                if kind is bool:
                    variable = tk.BooleanVar(value=value)
                    widget = tk.Checkbutton(form, text=caption, variable=variable, bg=PANEL, fg=TEXT,
                        selectcolor='#163947', activebackground=PANEL, activeforeground=CYAN, anchor='w', font=('Segoe UI', 10))
                    widget.pack(fill='x', pady=7)
                    self.values[path] = (kind, variable)
                else:
                    label(form, caption, 10, MUTED).pack(anchor='w', pady=(8, 4))
                    if kind in (dict, list):
                        widget = text_box(form, height=min(8, max(3, len(value)+2)), width=30)
                        widget.insert('1.0', json.dumps(value, indent=2))
                        widget.pack(fill='x', pady=(0, 8))
                        self.values[path] = (kind, widget)
                    else:
                        variable = tk.StringVar(value='' if value is None else str(value))
                        widget = tk.Entry(form, textvariable=variable, bg='#0b2030', fg=TEXT,
                                          insertbackground=CYAN, relief='flat', font=('Consolas', 11))
                        widget.pack(fill='x', ipady=7, pady=(0, 6))
                        self.values[path] = (kind, variable)
            self.panels[section] = frame
        def select(_=None):
            if not nav.curselection(): return
            for p in self.panels.values(): p.pack_forget()
            self.panels[nav.get(nav.curselection()[0])].pack(fill='both', expand=True)
        nav.bind('<<ListboxSelect>>', select)
        nav.selection_set(0)
        select()
        button(self.window, 'SAVE CONFIGURATION', self.save, True).pack(anchor='e', padx=20, pady=16)

    def save(self):
        config = copy.deepcopy(self.config)
        try:
            for path, (kind, widget) in self.values.items():
                if kind in (dict, list):
                    value = json.loads(widget.get('1.0', 'end'))
                    if not isinstance(value, kind): raise ValueError(f'{path} has the wrong structure.')
                elif kind == 'optional_int': value = int(widget.get()) if widget.get().strip() else None
                elif kind == 'optional_float': value = float(widget.get()) if widget.get().strip() else None
                else: value = kind(widget.get())
                set_value(config, path, value)
            validate(config)
        except Exception as exc:
            messagebox.showerror('Check configuration', str(exc), parent=self.window)
            return
        # Registry and disk operations run off Tk's thread. Applying this user-selected
        # checkbox is the only place automatic startup is enabled or disabled.
        def persist():
            old = self.config['desktop']['start_with_windows']
            new = config['desktop']['start_with_windows']
            if old != new: Startup.set_enabled(self.desktop.assistant.root, new)
            try:
                save_config(self.desktop.assistant.root, config)
            except Exception:
                if old != new: Startup.set_enabled(self.desktop.assistant.root, old)
                raise
            return 'Configuration saved. Restart JARVIS to apply changes.'
        self.desktop.background(persist, lambda result: self.saved(result))

    def saved(self, result):
        self.desktop.notify(result)
        if self.window.winfo_exists(): self.window.destroy()
