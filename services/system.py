import asyncio
import ctypes
import os
import subprocess
from datetime import datetime
from pathlib import Path
from core.diagnostics import failure

def screenshot_name(now=None):
    return (now or datetime.now()).strftime('JARVIS_%Y-%m-%d_%H-%M-%S-%f.png')

class System:
    def __init__(self, root):
        self.root = root

    def volume(self, action):
        import comtypes
        comtypes.CoInitialize()
        try:
            from pycaw.pycaw import AudioUtilities
            endpoint = AudioUtilities.GetSpeakers().EndpointVolume
            if action in ('mute', 'unmute'):
                endpoint.SetMute(action == 'mute', None)
            else:
                delta = 0.1 if action == 'volume_up' else -0.1
                endpoint.SetMasterVolumeLevelScalar(max(0, min(1, endpoint.GetMasterVolumeLevelScalar() + delta)), None)
            return 'Volume updated.'
        finally:
            comtypes.CoUninitialize()

    def media(self, action):
        async def control():
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if session is None:
                return 'No active media session. Open Spotify and select a track first.'
            method = {'play': 'try_play_async', 'pause': 'try_pause_async',
                      'toggle_media': 'try_toggle_play_pause_async',
                      'next': 'try_skip_next_async', 'previous': 'try_skip_previous_async'}[action]
            success = await getattr(session, method)()
            return f'Media command {action} sent.' if success else 'The current media player did not accept that command.'
        return asyncio.run(control())

    def media_metadata(self):
        async def read():
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = manager.get_current_session()
            if not session:
                return None
            properties = await session.try_get_media_properties_async()
            return {'title': properties.title, 'artist': properties.artist}
        try:
            async def bounded():
                return await asyncio.wait_for(read(), timeout=3)
            return asyncio.run(bounded())
        except Exception as exc:
            failure('media-metadata', exc)
            return None

    def screenshot(self):
        from PIL import ImageGrab
        folder = self.root / 'data/screenshots'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / screenshot_name()
        ImageGrab.grab(all_screens=True).save(path)
        return 'Screenshot captured. Saved in your JARVIS screenshots folder.'

    def show_desktop(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            win32com.client.Dispatch('Shell.Application').MinimizeAll()
        finally:
            pythoncom.CoUninitialize()
        return 'Showing desktop.'

    def minimize_window(self):
        import win32gui
        import win32con
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            raise ValueError('No foreground window is available.')
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return 'Window minimized.'

    def switch_window(self, name):
        from services.apps import canonical, APPS
        import psutil
        import win32gui
        import win32process
        import win32con
        key = canonical(name)
        if not key:
            raise ValueError('Choose an application from the configured application list.')
        pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if (p.info['name'] or '').lower() == APPS[key][1].lower()}
        found = []
        win32gui.EnumWindows(lambda hwnd, _: found.append(hwnd) if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] in pids else None, None)
        if not found:
            raise ValueError(f'No visible {APPS[key][0]} window was found.')
        win32gui.ShowWindow(found[0], win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(found[0])
        except Exception as exc:
            failure('window-foreground', exc)
            raise ValueError('Windows blocked focus switching. Select the application on the taskbar.') from exc
        return f'Switched to {APPS[key][0]}.'

    def open_safe_file(self, path):
        path = Path(path)
        if not path.exists():
            raise ValueError('That search result no longer exists.')
        if not path.is_dir() and path.suffix.lower() not in ('.pdf', '.txt', '.png', '.jpg', '.jpeg'):
            raise ValueError('Direct open is limited to folders, PDF, text and images. Use Open location for other file types.')
        os.startfile(str(path))
        return 'Opening selected result.'

    def battery(self):
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return 'Windows did not report a battery.'
        return f'Battery is at {battery.percent:.0f} percent' + (' and plugged in.' if battery.power_plugged else '.')

    def lock(self):
        if not ctypes.windll.user32.LockWorkStation():
            raise OSError('Windows could not lock the workstation.')
        return 'Locking your computer.'

    def power(self, action):
        exe = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/shutdown.exe'
        subprocess.run([str(exe), '/s' if action == 'shutdown' else '/r', '/t', '0'], check=True, shell=False)
        return 'Power command sent to Windows.'

    def reveal(self, path):
        if not Path(path).exists():
            raise ValueError('That search result no longer exists.')
        subprocess.Popen(['explorer.exe', '/select,', str(path)], shell=False)
        return 'Revealing the result in File Explorer.'
