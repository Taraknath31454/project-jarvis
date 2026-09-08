"""Non-destructive GUI smoke test; no microphone, speech, or automation."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import load_config
from core.assistant import Assistant
from ui.desktop import Desktop

def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        config, _ = load_config(root)
        config['tts']['enabled'] = False
        desktop = Desktop(Assistant(root, config), integrations=False)
        desktop.root.geometry('1280x680+10+10')
        errors = []
        desktop.root.report_callback_exception = lambda *error: errors.append(str(error))
        desktop.root.after(100, lambda: desktop.submit('what time is it'))
        def verify():
            try:
                assert 'It is' in desktop.output.get('1.0', 'end')
                assert not desktop.processing.is_set()
                assert desktop.mic_active is False
                assert desktop.entry.winfo_ismapped()
                assert desktop.mic_button.winfo_ismapped()
                assert desktop.graph.winfo_height() >= 30, f'Graph clipped: {desktop.graph.winfo_height()} px'
                assert desktop.mic_button.winfo_rooty()+desktop.mic_button.winfo_height() <= desktop.dashboard.winfo_rooty()+desktop.dashboard.winfo_height()
                assert desktop.entry.winfo_rooty() + desktop.entry.winfo_height() <= desktop.root.winfo_rooty() + desktop.root.winfo_height()
                assert not errors, errors
                from PIL import ImageGrab
                window = desktop.root
                screenshot = Path(__file__).resolve().parents[1] / 'data/desktop-preview.png'
                screenshot.parent.mkdir(exist_ok=True)
                import win32gui
                hwnd = win32gui.GetAncestor(window.winfo_id(), 2)
                ImageGrab.grab(window=hwnd).save(screenshot)
                print('PASS: desktop startup, typed command, event queue, idle state, mic off, screenshot.')
            except Exception as exc:
                errors.append(str(exc))
            finally:
                desktop.close()
        desktop.root.after(4200, verify)
        desktop.run()
        if errors:
            raise RuntimeError(errors)

if __name__ == '__main__':
    main()
