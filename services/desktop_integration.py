"""Opt-in Windows startup, tray and RegisterHotKey integration."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from core.diagnostics import failure

def parse_hotkey(text: str) -> tuple[int, int]:
    if not isinstance(text, str):
        raise ValueError('Hotkey must be a string such as ctrl+alt+j.')
    parts = text.lower().replace(' ', '').split('+')
    modifiers = {'alt': 1, 'ctrl': 2, 'shift': 4}
    if len(parts) < 3 or len(set(parts)) != len(parts) or not {'ctrl', 'alt'}.issubset(parts[:-1]) or any(p not in modifiers for p in parts[:-1]) or len(parts[-1]) != 1 or not parts[-1].isascii() or not parts[-1].isalpha():
        raise ValueError('Use Ctrl+Alt plus a letter, optionally Shift (example: ctrl+alt+j).')
    return sum(modifiers[p] for p in parts[:-1]) | 0x4000, ord(parts[-1].upper())

class Startup:
    """Owns only JARVIS's HKCU Run value. Never needs administrator privileges."""
    NAME = 'JARVIS Personal AI'
    KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'

    @classmethod
    def set_enabled(cls, root: Path, enabled: bool) -> None:
        if os.name != 'nt':
            raise ValueError('Windows startup integration is unavailable on this OS.')
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.KEY) as key:
            if enabled:
                interpreter = Path(sys.executable).with_name('pythonw.exe')
                if not interpreter.is_file():
                    interpreter = Path(sys.executable)
                command = subprocess.list2cmdline([str(interpreter), str(root / 'main.py')])
                winreg.SetValueEx(key, cls.NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, cls.NAME)
                except FileNotFoundError:
                    pass

class Hotkey:
    def __init__(self, text: str, events: queue.Queue):
        self.text, self.events = text, events
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.registered = False
        self.thread_id = None
        self.thread = threading.Thread(target=self._run, daemon=True, name='jarvis-hotkey')

    def start(self):
        self.thread.start()

    def _run(self):
        user32 = ctypes.windll.user32
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        modifiers, key = parse_hotkey(self.text)
        if not user32.RegisterHotKey(None, 1, modifiers, key):
            self.events.put(('notification', 'Global hotkey unavailable; another application may be using it.'))
            self.ready.set()
            return
        self.registered = True
        self.ready.set()
        try:
            message = wintypes.MSG()
            while not self.stop_event.wait(0.06):
                while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                    if message.message == 0x0312:
                        self.events.put(('foreground', None))
        finally:
            user32.UnregisterHotKey(None, 1)
            self.registered = False

    def stop(self):
        self.stop_event.set()

class Tray:
    def __init__(self, events):
        self.events, self.icon = events, None

    def start(self) -> bool:
        try:
            import pystray
            from PIL import Image, ImageDraw
            image = Image.new('RGBA', (64, 64), '#030811')
            draw = ImageDraw.Draw(image)
            draw.ellipse((6, 6, 58, 58), outline='#29e5e5', width=4)
            draw.line((38, 18, 38, 40, 30, 47, 22, 40), fill='#29e5e5', width=5)
            def send(kind, value=None):
                return lambda *_: self.events.put((kind, value))
            self.icon = pystray.Icon('jarvis', image, 'JARVIS • Personal AI System', pystray.Menu(
                pystray.MenuItem('Open JARVIS', send('foreground'), default=True),
                pystray.MenuItem('Enable microphone', send('mic_request', True)),
                pystray.MenuItem('Disable microphone', send('mic_request', False)),
                pystray.MenuItem('Settings', send('settings')),
                pystray.MenuItem('Exit JARVIS', send('exit'))))
            self.icon.run_detached()
            return True
        except Exception as exc:
            failure('tray', exc)
            self.events.put(('notification', 'System tray unavailable. The window will remain accessible.'))
            return False

    def stop(self):
        if self.icon:
            self.icon.stop()
