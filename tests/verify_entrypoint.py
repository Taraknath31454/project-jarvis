"""Launch the real entry point, capture only its window, and close only its process's window."""
from pathlib import Path
import subprocess
import sys
import time
import win32gui
import win32process
import win32con
import psutil
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]

def main():
    with (ROOT/'data/entrypoint-check.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(ROOT/'main.py')], cwd=ROOT, stdout=log, stderr=log)
        hwnd = None
        try:
            deadline = time.monotonic()+12
            while time.monotonic() < deadline:
                windows = []
                # Windows Store/venv launchers can delegate to a child interpreter.
                owned = {process.pid, *(child.pid for child in psutil.Process(process.pid).children(recursive=True))}
                def enum_cb(handle, _):
                    if win32process.GetWindowThreadProcessId(handle)[1] in owned and 'JARVIS V2' in win32gui.GetWindowText(handle):
                        windows.append(handle)
                    return True
                try:
                    win32gui.EnumWindows(enum_cb, None)
                except Exception:
                    pass
                if windows:
                    hwnd = windows[0]
                    break
                assert process.poll() is None, 'Entry point exited before showing its window.'
                time.sleep(.1)
            assert hwnd, 'Entry point did not create a window.'
            sample = psutil.Process(win32process.GetWindowThreadProcessId(hwnd)[1])
            time.sleep(4)  # exclude startup imports and first telemetry initialization
            cpu = sample.cpu_percent(interval=4)
            ImageGrab.grab(window=hwnd).save(ROOT/'data/jarvis-v2-final.png')
            print(f'PASS: real main.py launched; settled idle CPU sample {cpu:.1f}% of one CPU core ({cpu/psutil.cpu_count():.2f}% of total logical capacity).')
        finally:
            if hwnd and win32gui.IsWindow(hwnd): win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            try:
                process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                # Only the subprocess created by this test; no user app process is touched.
                process.terminate()
                process.wait(timeout=3)
        assert process.returncode == 0, 'Entry point exited with an error; inspect data/entrypoint-check.log.'
        print('PASS: normal window close and clean application exit.')

if __name__ == '__main__': main()
