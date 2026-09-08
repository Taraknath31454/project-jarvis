"""Real Tk/SAPI integration checks. Safe time command only; no app automation.

Run manually on Windows. Generates window-only QA screenshots, verifies layouts,
and exercises the GUI voice event path with real TTS (not acoustic recognition).
"""
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.assistant import Assistant
from core.config import load_config
from ui.desktop import Desktop
from PIL import ImageGrab
import win32gui

ROOT = Path(__file__).resolve().parents[1]

def pump(desktop, seconds):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        desktop.root.update()
        time.sleep(.01)

def capture(window, name):
    window.update_idletasks()
    hwnd = win32gui.GetAncestor(window.winfo_id(), 2)
    ImageGrab.grab(window=hwnd).save(ROOT/'data'/name)

def main():
    with tempfile.TemporaryDirectory() as temp:
        config, _ = load_config(Path(temp))
        config['desktop']['global_hotkey_enabled'] = False
        desktop = Desktop(Assistant(Path(temp), config), integrations=False)
        errors = []
        desktop.root.report_callback_exception = lambda *error: errors.append(str(error))
        try:
            for width, height, name in [(1280, 680, 'v2-1366.png'), (1840, 980, 'v2-1920.png'), (2480, 1340, 'v2-2560.png')]:
                desktop.root.geometry(f'{width}x{height}+0+0')
                pump(desktop, .6)
                for widget in (desktop.entry, desktop.mic_button, desktop.media_label, desktop.graph):
                    assert widget.winfo_ismapped(), str(widget)
                    assert widget.winfo_rooty()+widget.winfo_height() <= desktop.root.winfo_rooty()+desktop.root.winfo_height()
                assert desktop.graph.winfo_height() >= 30
                assert desktop.core.winfo_height() >= 140
                capture(desktop.root, name)
            desktop.root.geometry('1280x680+10+10')
            pump(desktop, .2)
            desktop.root.event_generate('<F11>')
            pump(desktop, .2)
            assert desktop.fullscreen
            desktop.root.event_generate('<Escape>')
            pump(desktop, .2)
            assert not desktop.fullscreen
            window = desktop.palette(True)
            pump(desktop, .2)
            capture(window, 'v2-commands.png')
            window.destroy()
            settings = desktop.settings()
            pump(desktop, .3)
            capture(settings.window, 'v2-settings.png')
            settings.window.destroy()
            # Deliberately feed a known transcript through the exact voice event queue.
            # Only a safe time command runs; actual SAPI output and its busy state are used.
            flow = [desktop.status.get()]
            desktop.mic_requested = desktop.mic_active = True
            desktop.events.put(('audio_level', .5))
            pump(desktop, .12)
            flow.append(desktop.status.get())
            actual = desktop.assistant.execute
            def execute(text):
                assert text == 'what time is it'
                time.sleep(.18)  # test-only: expose processing for a sampled frame
                return actual(text)
            with patch.object(desktop.assistant, 'execute', side_effect=execute):
                desktop.events.put(('voice', 'what time is it'))
                end = time.monotonic()+12
                while time.monotonic() < end:
                    pump(desktop, .025)
                    state = desktop.status.get()
                    if state != flow[-1]: flow.append(state)
                    if 'Speaking' in flow and state == 'Idle': break
            assert flow == ['Idle', 'Listening', 'Processing', 'Speaking', 'Idle'], flow
            assert 'It is' in desktop.output.get('1.0', 'end')
            desktop.mic_requested = desktop.mic_active = False
            print('PASS: voice event + real SAPI state flow:', ' -> '.join(flow))
            print('PASS: 1366/1920/2560 layouts, F11/Esc, help, settings, no Tk callback errors.')
            assert not errors, errors
        finally:
            desktop.close()

if __name__ == '__main__': main()
