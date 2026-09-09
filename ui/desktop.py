"""Tk controller. Worker results cross a queue; all UI updates stay on Tk's thread."""
import ctypes
import math
import os
import queue
import threading
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import simpledialog
from core.assistant import SENSITIVE
from core.diagnostics import failure
from services.voice import Speaker, Microphone
from services.dashboard import DashboardFeed
from services.desktop_integration import Hotkey, Tray
from ui.theme import BG, PANEL, CYAN, GLOW, TEXT, MUTED, AMBER, label, button, configure_ttk, set_text
from ui.widgets.telemetry import rate
from ui.widgets.hologram import mix
from ui.state import AssistantState

class Desktop:
    def __init__(self, assistant, first_run=False, *, integrations=True):
        self.assistant, self.config = assistant, assistant.config
        if os.name == 'nt':
            try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError): pass
        self.root = tk.Tk()
        self.root.title('JARVIS V2 • Personal AI Command Center')
        self.root.tk.call('tk', 'scaling', 1.33333)
        self.root.geometry(f'{min(1440, self.root.winfo_screenwidth()-60)}x{min(880, self.root.winfo_screenheight()-90)}+20+20')
        self.root.minsize(1060, 630)
        self.root.configure(bg=BG)
        configure_ttk(self.root)
        self.events = queue.Queue()
        self.processing = threading.Event()
        self.speaker = Speaker(self.config['tts'], self.events)
        self.mic = Microphone(assistant.root, self.config['microphone'], self.events, self.speaker.busy, self.processing)
        self.state_model = AssistantState()
        self.status = tk.StringVar(value='Idle')
        self.mic_label = tk.StringVar(value='MICROPHONE: STANDBY')
        self.recognized = tk.StringVar(value='At your service.')
        self.voice_prompt = tk.StringVar(value='STANDBY / TYPE A COMMAND')
        self.mic_active = self.mic_requested = self.closed = self.fullscreen = False
        self.current_command = ''
        self.interactions = deque(maxlen=self.config['privacy']['transcript_limit'])
        self.notifications = deque(maxlen=20)
        self.reminders_shown = set()
        self.upcoming, self.latest_history = [], []
        self.last_network = None
        self.battery_warned = False
        self.tray = self.hotkey = None
        self.feed = DashboardFeed(assistant, self.events)
        self.last_tick = time.monotonic()
        from ui.dashboard_layout import build
        build(self)
        self.root.protocol('WM_DELETE_WINDOW', self.request_close)
        self.root.report_callback_exception = self.callback_error
        self.root.bind('<Control-space>', self.focus_input)
        self.root.bind('<Control-k>', lambda _: self.palette())
        self.root.bind('<F11>', lambda _: self.toggle_fullscreen())
        self.root.bind('<Escape>', lambda _: self.toggle_fullscreen(False))
        self.core.intensity = self.config['dashboard']['animation_intensity']
        self.root.after(30, self.poll)
        self.root.after(30, self.animate)
        self.root.after(100, self.clock)
        self.feed.start()
        self.notify('Command router ready. Local storage connected. Microphone is opt-in.')
        self.reply(self.greeting())
        if integrations: self.setup_integrations()
        if self.config['dashboard']['fullscreen']: self.toggle_fullscreen(True)
        if self.config['desktop']['start_minimized'] and integrations: self.root.after(200, self.hide)
        if self.config['desktop']['startup_greeting']: self.speaker.say(self.greeting())
        if self.config['desktop']['startup_sound'] and integrations: self.background(self.startup_tone)
        if first_run: self.notify('Welcome. Configure Chrome profiles and folders in Settings.')

    def greeting(self):
        hour = datetime.now().hour
        period = 'morning' if hour < 12 else 'afternoon' if hour < 18 else 'evening'
        return f'Good {period}. {self.config["assistant_name"]} online. At your service.'

    def reply(self, message):
        set_text(self.output, message)
        for index, line in enumerate(message.splitlines(), 1):
            if line.startswith('YOU >'):
                self.output.tag_add('you', f'{index}.0', f'{index}.end')
            elif line.startswith('JARVIS'):
                self.output.tag_add('speaker', f'{index}.0', f'{index}.6')

    def refresh_history(self): self.background(self.assistant.storage.recent, self.show_history)

    def show_history(self, rows):
        changed = rows != self.latest_history
        self.latest_history = rows
        names = {'screenshot': 'Screenshot saved', 'reminder': 'Reminder created', 'note': 'Note saved', 'open': 'Launch requested'}
        set_text(self.history, '\n'.join(f'{stamp[11:16]}  {"✓" if ok else "!"}  {names.get(command, command.capitalize())}' for stamp, command, ok in rows[:6]))
        if changed:
            self.history_reveal = 0.

    def submit(self, text=None):
        if self.processing.is_set() or self.speaker.busy.is_set():
            self.notify('Finish the current response before sending another command.')
            return
        text = self.entry.get().strip() if text is None else text.strip()
        if not text: return
        self.entry.delete(0, 'end')
        self.current_command = text
        self.recognized.set('[Private input omitted]' if SENSITIVE.search(text) else text[:250])
        self.processing.set()
        self.status.set('Processing')
        def work():
            try: self.events.put(('result', self.assistant.execute(text)))
            except Exception as exc:
                failure('command-worker', exc)
                self.events.put(('notice', 'Local storage unavailable. Check disk space and data folder permissions.'))
                self.events.put(('processing_done', None))
        threading.Thread(target=work, daemon=True, name='jarvis-command').start()

    def background(self, operation, callback=None):
        def work():
            try:
                value = operation()
                if callback: self.events.put(('callback', (callback, value)))
            except Exception as exc:
                failure('desktop-task', exc)
                self.events.put(('notice', 'Unable to complete the requested operation. See the diagnostic log.'))
        threading.Thread(target=work, daemon=True, name='jarvis-ui-service').start()

    def toggle_mic(self): self.set_mic(not self.mic_requested)

    def set_mic(self, enabled):
        if enabled and not self.mic_requested:
            if self.mic.thread and self.mic.thread.is_alive():
                self.notify('Microphone is still stopping. Try again shortly.')
                return
            self.mic_requested = True
            self.mic_button.configure(text='◉ DISABLE MICROPHONE')
            self.mic_label.set('MICROPHONE: INITIALIZING')
            self.mic.start()
        elif not enabled:
            self.mic_requested = False
            self.mic.stop()
            self.mic_button.configure(text='◉ ENABLE MICROPHONE')

    def handle_result(self, result):
        self.processing.clear()
        private = result.action in ('note', 'reminder', 'clipboard_read', 'clipboard_note', 'list_notes', 'list_reminders', 'find', 'google', 'youtube', 'private_input', 'unknown')
        prompt = result.action.replace('_', ' ') + ' [content omitted]' if private else self.current_command[:250]
        response = 'Content shown in the current response only.' if result.action in ('clipboard_read', 'list_notes', 'list_reminders', 'find') else result.message
        if self.config['privacy']['transcript_enabled']:
            self.interactions.append((prompt, response))
            previous = '\n\n'.join(f'YOU > {p}\nJARVIS  {r}' for p, r in list(self.interactions)[:-1])
            self.reply((previous+'\n\n' if previous else '') + f'YOU > {prompt}\nJARVIS  {result.message}')
            self.output.see('end')
        else: self.reply(result.message)
        self.current_command = ''
        if not result.success:
            self.state_model.error()
            self.notify(result.message)
        if result.action == 'find' and result.success and self.assistant.files.results:
            from ui.dialogs import file_results
            file_results(self, list(self.assistant.files.results))
        self.refresh_history()
        if result.speak and not result.exit: self.speaker.say(result.message)
        if result.exit: self.close()

    def poll(self):
        if self.closed: return
        for _ in range(100):
            try: kind, value = self.events.get_nowait()
            except queue.Empty: break
            if kind == 'result': self.handle_result(value)
            elif kind == 'voice' and self.mic_requested:
                self.state_model.listening_until = time.monotonic()+.8
                self.submit(value or self.config['microphone']['wake_word'])
            elif kind in ('notice', 'notification'):
                self.notify(value)
                if kind == 'notice':
                    self.reply(value)
                    self.state_model.error()
            elif kind == 'processing_done': self.processing.clear()
            elif kind == 'audio_level': self.state_model.audio(value)
            elif kind == 'mic':
                self.mic_active = value
                if not value: self.mic_requested = False
                self.mic_label.set('MICROPHONE: ACTIVE' if value else 'MICROPHONE: STANDBY')
                self.mic_button.configure(text='◉ DISABLE MICROPHONE' if value else '◉ ENABLE MICROPHONE')
            elif kind == 'telemetry': self.show_telemetry(value)
            elif kind == 'network': self.show_network(value)
            elif kind == 'weather': self.show_weather(value)
            elif kind == 'local_data': self.show_local(value)
            elif kind == 'media':
                text = (value.get('title', '')+' — '+value.get('artist', '')).strip(' —') if value else ''
                self.media_label.configure(text=text[:52] if text else 'MEDIA / No active session')
            elif kind == 'callback': value[0](value[1])
            elif kind == 'foreground': self.foreground()
            elif kind == 'settings': self.settings()
            elif kind == 'mic_request': self.set_mic(value)
            elif kind == 'exit': self.close()
            if self.closed: return
        state = self.state_model.resolve(self.processing.is_set(), self.speaker.busy.is_set(), self.mic_active)
        self.status.set(state)
        self.state_label.configure(text='STANDBY' if state == 'Idle' and not self.mic_active else state.upper(), fg=AMBER if state in ('Error', 'Offline') else CYAN)
        prompts = {'Listening': "I'M LISTENING...", 'Processing': 'ANALYZING REQUEST...',
                   'Speaking': 'JARVIS IS SPEAKING...', 'Error': 'SIGNAL INTERRUPTED',
                   'Offline': 'LOCAL CORE OFFLINE'}
        self.voice_prompt.set(prompts.get(state, 'SPEAK ANYTIME' if self.mic_active else 'STANDBY / TYPE A COMMAND'))
        self.voice_caption.configure(fg=AMBER if state in ('Error', 'Offline') else GLOW if state in ('Listening', 'Speaking') else CYAN)
        self.root.after(40, self.poll)

    def animate(self):
        if self.closed: return
        now = time.monotonic()
        dt, self.last_tick = min(.1, now-self.last_tick), now
        hidden = self.root.state() in ('iconic', 'withdrawn')
        if not hidden:
            self.adapt_layout()
            self.core.tick(dt, self.status.get(), self.state_model.level, self.mic_active)
            state = self.status.get()
            edge = mix(AMBER if state == 'Error' else CYAN,
                       .18 + .14 * (1 + math.sin(self.core.elapsed * 1.5)) / 2 + .22*self.core.reaction)
            self.core_panel.configure(highlightbackground=edge)
            # Subtle breathing glow on side panels
            subtle = mix(CYAN, .08 + .05 * (1 + math.sin(self.core.elapsed * .7)) / 2)
            for attr in ('left_panel', 'right_panel'):
                p = getattr(self, attr, None)
                if p: p.configure(highlightbackground=subtle)
            self.waveform.tick(state, self.state_model.level, dt*self.core.intensity, self.core.elapsed)
            self.transcript_panel.configure(highlightbackground=edge)
            self.terminal.configure(highlightbackground=mix(CYAN, .55 if self.root.focus_get() is self.entry else .16+.3*self.core.reaction))
            self.mic_indicator.configure(fg=mix(CYAN, .6+.4*self.core.reaction) if self.mic_active else MUTED)
            # Activity fades only on data changes, never on every feed refresh.
            reveal = min(1., getattr(self, 'history_reveal', 1.) + dt*2.5)
            if reveal != getattr(self, 'history_reveal', 1.):
                self.history.configure(fg=mix(TEXT, .25+.75*reveal))
                self.history_reveal = reveal
            for panel in (self.core_panel, self.left_panel, self.right_panel):
                sweep = getattr(panel, 'sweep', None)
                if sweep:
                    width = sweep.winfo_width()
                    x = ((self.core.elapsed*.12) % 1)*(width+70)-70
                    sweep.coords(panel.sweep_item, x, 1, x+70, 1)
                    sweep.itemconfigure(panel.sweep_item, fill=edge)
            for gauge in self.gauges.values(): gauge.tick()
        fps = min(20, self.config['dashboard']['fps']) if self.status.get() == 'Idle' else self.config['dashboard']['fps']
        # Allow Tk's deferred painting and queued input a full interval on busy frames.
        delay = round(1000/fps)
        self.root.after(500 if hidden else delay, self.animate)

    def show_telemetry(self, data):
        self.telemetry = data
        for key, gauge in self.gauges.items(): gauge.value = data.get(key)
        self.graph.add(data)
        gpu = f'{data["gpu"]:.0f}%' if data.get('gpu') is not None else 'N/A'
        charging = 'PLUGGED IN' if data.get('charging') else 'ON BATTERY' if data.get('battery') is not None else 'N/A'
        seconds = data.get('uptime')
        uptime = f'{int(seconds)//3600}h {int(seconds)%3600//60:02d}m' if seconds is not None else 'N/A'
        self.hardware_label.configure(text=f'GPU {gpu} • {charging}\nPROCESSES {data.get("processes") or "N/A"} • UP {uptime}')
        self.device_label.configure(text=f'{data.get("device", "N/A")} / {data.get("os", "N/A")}'[:44])
        self.update_network_label()
        battery = data.get('battery')
        if battery is not None and not data.get('charging') and battery <= self.config['monitor']['low_battery_percent']:
            if not self.battery_warned and self.config['monitor']['low_battery_warning']:
                self.notify(f'Battery low: {battery:.0f}%. Connect your charger.')
                self.battery_warned = True
        elif data.get('charging') or (battery is not None and battery > self.config['monitor']['low_battery_percent']+5):
            self.battery_warned = False

    def update_network_label(self):
        network = self.last_network or {'internet': 'N/A', 'wifi': 'N/A'}
        data = getattr(self, 'telemetry', {})
        self.network_label.configure(text=f'INTERNET {network["internet"]} / WI-FI {network["wifi"]}\n↓ {rate(data.get("download"))}   ↑ {rate(data.get("upload"))}')

    def show_network(self, value):
        if self.last_network and value['internet'] != self.last_network['internet']:
            self.notify('Internet connection '+('restored.' if value['internet'] == 'ONLINE' else 'unavailable. Local commands remain ready.'))
        self.last_network = value
        self.update_network_label()

    def show_weather(self, value):
        if value['status'] == 'ONLINE':
            text = f'{value["city"]} / {value["temperature"]:.0f}°C\n{value["condition"]} • Humidity {value["humidity"]:.0f}%\nOpen-Meteo • {value["time"][-5:]}'
        else: text = 'WEATHER OFFLINE' if value['status'] == 'OFFLINE' else 'WEATHER / OPTIONAL\nConfigure location in Settings'
        self.weather_label.configure(text=text)

    def show_local(self, data):
        self.upcoming = data['reminders']
        self.show_history(data['history'])
        self.reminder_label.configure(text='\n'.join(f'{due[11:16]}  {text[:32]}' for _, due, text in self.upcoming[:3]) or 'No pending reminders.')
        for rid, text in data['due']:
            if rid not in self.reminders_shown:
                self.reminders_shown.add(rid)
                self.notify('Reminder due. Open Upcoming → View all to dismiss.')
                self.speaker.say('You have a reminder. Check JARVIS.')
                self.reminder_popup(rid, text)

    def notify(self, message):
        if self.notifications and self.notifications[-1][1] == message: return
        self.notifications.append((datetime.now().strftime('%H:%M'), message))
        if hasattr(self, 'notification_label'):
            self.notification_label.configure(text='\n'.join(f'{stamp} {text[:90]}' for stamp, text in list(self.notifications)[-2:]))

    def clock(self):
        if self.closed: return
        self.clock_label.configure(text=datetime.now().strftime('%H:%M:%S\n%a • %d %b %Y'))
        network = (self.last_network or {}).get('internet', 'N/A')
        battery = getattr(self, 'telemetry', {}).get('battery')
        charge = f'{battery:.0f}%' if battery is not None else 'N/A'
        self.header_status.configure(text=f'● SYSTEM ONLINE / LOCAL MODE\nMIC {"ON" if self.mic_active else "OFF"} • NET {network} • BAT {charge}')
        self.root.after(1000, self.clock)

    def clear_history(self):
        self.interactions.clear()
        self.current_command = ''
        self.recognized.set('')
        self.reply('Transcript cleared.')
        self.background(self.assistant.storage.clear_history, lambda _: self.refresh_history())

    def new_note(self):
        text = simpledialog.askstring('JARVIS • New note', 'Note text (saved locally):', parent=self.root)
        if text and text.strip(): self.submit('remember note: '+text.strip())

    def notes(self):
        from ui.dialogs import notes_window
        notes_window(self)

    def reminders_window(self):
        window = tk.Toplevel(self.root)
        window.title('JARVIS • Upcoming reminders')
        window.geometry('630x420')
        window.configure(bg=BG)
        label(window, 'UPCOMING REMINDERS', 14, CYAN).pack(anchor='w', padx=20, pady=18)
        listing = tk.Listbox(window, bg=PANEL, fg=TEXT, selectbackground='#174153', relief='flat', font=('Segoe UI', 11))
        listing.pack(fill='both', expand=True, padx=20)
        rows = list(self.upcoming)
        for _, due, text in rows: listing.insert('end', f'{due[:16].replace("T", " ")}  {text}')
        def dismiss():
            if listing.curselection():
                index = listing.curselection()[0]
                rid = rows[index][0]
                self.background(lambda: self.assistant.storage.acknowledge(rid))
                listing.delete(index)
                rows.pop(index)
        button(window, 'DISMISS SELECTED', dismiss, True).pack(anchor='e', padx=20, pady=15)
        return window

    def reminder_popup(self, rid, text):
        window = tk.Toplevel(self.root)
        window.title('JARVIS • Reminder')
        window.geometry('440x200')
        window.configure(bg=PANEL)
        window.attributes('-topmost', True)
        label(window, 'REMINDER', 12, CYAN).pack(pady=15)
        label(window, text, 12, wraplength=390).pack(padx=20, pady=8)
        def dismiss():
            self.background(lambda: self.assistant.storage.acknowledge(rid))
            window.destroy()
        button(window, 'DISMISS', dismiss, True).pack(pady=10)
        window.protocol('WM_DELETE_WINDOW', dismiss)

    def palette(self, help_mode=False):
        from ui.dialogs import command_palette
        return command_palette(self, help_mode)

    def settings(self):
        from ui.settings_window import SettingsWindow
        return SettingsWindow(self)

    def focus_input(self, _=None):
        self.entry.focus_set()
        return 'break'

    def foreground(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()

    def toggle_fullscreen(self, value=None):
        self.fullscreen = not self.fullscreen if value is None else value
        self.root.attributes('-fullscreen', self.fullscreen)

    def maximize(self): self.root.state('normal' if self.root.state() == 'zoomed' else 'zoomed')

    def hide(self):
        if self.tray: self.root.withdraw()
        else: self.root.iconify()

    def setup_integrations(self):
        if self.config['desktop']['tray_enabled']:
            tray = Tray(self.events)
            if tray.start(): self.tray = tray
        if self.config['desktop']['global_hotkey_enabled'] and os.name == 'nt':
            self.hotkey = Hotkey(self.config['desktop']['global_hotkey'], self.events)
            self.hotkey.start()

    @staticmethod
    def startup_tone():
        import winsound
        winsound.Beep(740, 65)
        winsound.Beep(980, 65)

    def callback_error(self, kind, exc, tb):
        failure('tk-callback', exc)
        self.notify('Interface operation unavailable. See the diagnostic log.')
        self.state_model.error()

    def request_close(self):
        if self.config['desktop']['close_to_tray'] and self.tray:
            self.root.withdraw()
            self.notify('JARVIS is running in the tray. Microphone mode is unchanged.')
        else: self.close()

    def close(self):
        if self.closed: return
        self.closed = True
        self.mic.stop()
        self.feed.stop()
        if self.hotkey: self.hotkey.stop()
        if self.tray: self.tray.stop()
        self.speaker.queue.put(None)
        self.root.destroy()

    def run(self): self.root.mainloop()
