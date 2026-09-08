"""Opt-in local device checks. Captures briefly in memory; never dispatches speech."""
import ctypes
from pathlib import Path
import queue
import sys
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import load_config
from services.voice import Microphone
from services.desktop_integration import Hotkey, Tray

def main():
    root = Path(__file__).resolve().parents[1]
    config, _ = load_config(root)
    events = queue.Queue()
    mic = Microphone(root, config['microphone'], events, threading.Event(), threading.Event())
    mic.start()
    active = levels = False
    deadline = time.monotonic()+12
    failures = []
    try:
        while time.monotonic() < deadline:
            try: kind, value = events.get(timeout=.1)
            except queue.Empty: continue
            if kind == 'mic' and value: active = True
            if kind == 'audio_level': levels = True
            if kind == 'notice': failures.append(value)
            # Recognition events are deliberately discarded, never printed or executed.
            if active and levels: break
    finally:
        mic.stop()
        if mic.thread: mic.thread.join(timeout=3)
    assert active and levels, failures or 'Microphone did not produce samples.'
    assert not mic.thread.is_alive(), 'Microphone did not stop.'
    print('PASS: actual microphone stream, real amplitude, clean stop; audio was not saved or dispatched.')
    hotkey_events = queue.Queue()
    hotkey = Hotkey('ctrl+alt+j', hotkey_events)
    hotkey.start()
    assert hotkey.ready.wait(2), 'Hotkey worker did not initialize.'
    try:
        assert hotkey.registered, 'Default hotkey is already in use.'
        ctypes.windll.user32.PostThreadMessageW(hotkey.thread_id, 0x0312, 1, 0)
        assert hotkey_events.get(timeout=2)[0] == 'foreground'
    finally:
        hotkey.stop()
        hotkey.thread.join(timeout=2)
    assert not hotkey.registered
    print('PASS: RegisterHotKey, focus event, unregister; no keys were synthesized.')
    tray_events = queue.Queue()
    tray = Tray(tray_events)
    try:
        assert tray.start(), 'Tray initialization failed.'
        end = time.monotonic()+2
        while not tray.icon.visible and time.monotonic() < end: time.sleep(.02)
        assert tray.icon.visible
        tray.icon.menu.items[0](tray.icon)
        assert tray_events.get(timeout=2)[0] == 'foreground'
    finally:
        tray.stop()
    print('PASS: system tray icon, Open JARVIS callback, clean exit.')

if __name__ == '__main__': main()
