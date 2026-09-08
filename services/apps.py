"""Allowlisted Windows launches and graceful WM_CLOSE requests."""
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from core.config import expand_path
from core.diagnostics import failure

APPS = {
    'chrome': ('Google Chrome', 'chrome.exe', ['google chrome']),
    'whatsapp': ('WhatsApp', 'WhatsApp.exe', ['whats app']),
    'vscode': ('VS Code', 'Code.exe', ['vs code', 'visual studio code', 'code']),
    'explorer': ('File Explorer', 'explorer.exe', ['file explorer', 'windows explorer']),
    'notepad': ('Notepad', 'notepad.exe', []),
    'calculator': ('Calculator', 'calc.exe', ['calc']),
    'settings': ('Settings', 'SystemSettings.exe', ['windows settings']),
    'spotify': ('Spotify', 'Spotify.exe', []), 'steam': ('Steam', 'steam.exe', []),
    'discord': ('Discord', 'Discord.exe', []),
    'task manager': ('Task Manager', 'Taskmgr.exe', ['taskmanager']),
    'unity': ('Unity Hub', 'Unity Hub.exe', ['unity hub']),
    'blender': ('Blender', 'blender.exe', []),
}
PROTOCOLS = {'whatsapp': 'whatsapp:', 'spotify': 'spotify:', 'steam': 'steam://open/main',
             'discord': 'discord:', 'settings': 'ms-settings:'}
WINDOWS_TARGETS = {
    'bluetooth settings': ['ms-settings:bluetooth'], 'wi-fi settings': ['ms-settings:network-wifi'],
    'wifi settings': ['ms-settings:network-wifi'], 'display settings': ['ms-settings:display'],
    'sound settings': ['ms-settings:sound'], 'windows update': ['ms-settings:windowsupdate'],
    'installed apps': ['ms-settings:appsfeatures'], 'control panel': ['control.exe'],
    'device manager': ['mmc.exe', 'devmgmt.msc'],
    'recycle bin': ['explorer.exe', 'shell:RecycleBinFolder'],
}

def canonical(name):
    name = name.strip().lower()
    return next((key for key, (_, _, aliases) in APPS.items() if name in [key, *aliases]), None)

class Apps:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.cache = {}

    def discover_shortcut(self, key):
        """Resolve matching Start Menu shortcuts, never execute shortcut arguments."""
        if os.name != 'nt':
            return None
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            shell = win32com.client.Dispatch('WScript.Shell')
            names = {key, APPS[key][0].lower(), *APPS[key][2]}
            for env in ('APPDATA', 'PROGRAMDATA'):
                base = Path(os.environ.get(env, '')) / 'Microsoft/Windows/Start Menu/Programs'
                for count, path in enumerate(base.rglob('*.lnk')):
                    if count > 2500:
                        break
                    if not any(path.stem.lower() == name or path.stem.lower().startswith(name + ' ') for name in names):
                        continue
                    target = Path(shell.CreateShortcut(str(path)).TargetPath)
                    if target.name.lower() == APPS[key][1].lower() and target.is_file():
                        return str(target)
        except Exception as exc:
            failure('app-shortcuts', exc)
        finally:
            pythoncom.CoUninitialize()
        return None

    def executable(self, key):
        configured = self.config['chrome_executable'] if key == 'chrome' else ''
        configured = configured or self.config['app_paths'].get(key, '')
        if configured:
            path = expand_path(configured, self.root)
            if not path.is_file() or path.suffix.lower() != '.exe':
                raise ValueError(f'The configured {key} executable is invalid. Choose an existing .exe in settings.')
            return str(path)
        if key in self.cache and Path(self.cache[key]).is_file():
            return self.cache[key]
        exe = APPS[key][1]
        candidates = [shutil.which(exe)]
        if os.name == 'nt':
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, f'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe}', 0, winreg.KEY_READ | view) as registry:
                            candidates.append(winreg.QueryValue(registry, None).strip('"'))
                    except OSError:
                        pass
        relative = {'chrome': ['Google/Chrome/Application/chrome.exe'],
                    'vscode': ['Programs/Microsoft VS Code/Code.exe', 'Microsoft VS Code/Code.exe'],
                    'spotify': ['Spotify/Spotify.exe'], 'steam': ['Steam/steam.exe'],
                    'unity': ['Unity Hub/Unity Hub.exe']}.get(key, [])
        for env in ('LOCALAPPDATA', 'APPDATA', 'ProgramFiles', 'ProgramFiles(x86)'):
            for suffix in relative:
                if os.environ.get(env):
                    candidates.append(str(Path(os.environ[env]) / suffix))
        if key == 'discord' and os.environ.get('LOCALAPPDATA'):
            candidates.extend(str(p) for p in sorted((Path(os.environ['LOCALAPPDATA']) / 'Discord').glob('app-*/Discord.exe'), reverse=True))
        if key == 'blender' and os.environ.get('ProgramFiles'):
            candidates.extend(str(p) for p in sorted((Path(os.environ['ProgramFiles']) / 'Blender Foundation').glob('Blender */blender.exe'), reverse=True))
        found = next((str(p) for p in candidates if p and Path(p).is_file()), None)
        found = found or self.discover_shortcut(key)
        if found:
            self.cache[key] = found
        return found

    def chrome(self, url=None, profile=None):
        exe = self.executable('chrome')
        if not exe:
            raise ValueError('Chrome was not found. Install Chrome or set chrome_executable in settings.')
        args = [exe]
        if profile:
            profiles = {k.lower(): v for k, v in self.config['chrome_profiles'].items()}
            if profile.lower() not in profiles:
                raise ValueError('That Chrome profile is not mapped. Add its name and directory in chrome_profiles.')
            directory = profiles[profile.lower()]
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data'
            if not (base / directory).is_dir():
                raise ValueError('The mapped Chrome profile directory does not exist in the default Chrome user-data folder.')
            args.append('--profile-directory=' + directory)
        if url:
            args.append(url)
        subprocess.Popen(args, shell=False)

    def open(self, name):
        lower = name.lower().strip()
        lower = {k.lower(): v.lower() for k, v in self.config.get('app_aliases', {}).items()}.get(lower, lower)
        if lower in WINDOWS_TARGETS:
            target = WINDOWS_TARGETS[lower]
            if target[0].startswith('ms-settings:'):
                os.startfile(target[0])
            else:
                exe = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32' / target[0]
                subprocess.Popen([str(exe), *target[1:]], shell=False)
            return f'Opening {lower}.'
        if lower in ('screenshots', 'screenshot folder'):
            path = self.root / 'data/screenshots'
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path))
            return 'Opening screenshots.'
        match = re.fullmatch(r'(?:google chrome|chrome)(?: (.+))?', lower)
        if match:
            profile = re.sub(r'^(?:profile|with profile) ', '', match[1]) if match[1] else None
            self.chrome(profile=profile)
            return 'Opening Chrome' + (f' with profile {profile}.' if profile else '.')
        websites = {k.lower(): v for k, v in self.config['website_aliases'].items()}
        folders = {k.lower(): v for k, v in self.config['folder_aliases'].items()}
        if lower in websites:
            self.chrome(url=websites[lower])
            return f'Opening {name} in Chrome.'
        if lower in folders:
            if not folders[lower]:
                raise ValueError(f'Set the folder_aliases entry for {name} in settings first.')
            path = expand_path(folders[lower], self.root)
            if not path.exists():
                raise ValueError('That configured path does not exist. Update folder_aliases in settings.')
            if not path.is_dir() and path.suffix.lower() not in ('.pdf', '.txt', '.png', '.jpg', '.jpeg'):
                raise ValueError('This file type cannot be opened through aliases. Use a folder or a PDF, text, or image file.')
            os.startfile(str(path))
            return f'Opening {name}.'
        key = canonical(lower)
        if not key:
            raise ValueError('Unknown app, website, or folder alias. Add it in settings or type help.')
        path = self.executable(key)
        if path:
            subprocess.Popen([path], shell=False)
        elif key in PROTOCOLS:
            os.startfile(PROTOCOLS[key])
        else:
            raise ValueError(f'{APPS[key][0]} was not found. Install it or set app_paths.{key}.')
        return f'Opening {APPS[key][0]}.'

    def search(self, engine, query):
        base, parameter = ('https://www.google.com/search', 'q') if engine == 'google' else ('https://www.youtube.com/results', 'search_query')
        self.chrome(url=base + '?' + urlencode({parameter: query}))
        return f'Opening {engine.title()} search results.'

    def close(self, key):
        if key in ('explorer', 'settings', 'task manager'):
            raise ValueError('Closing this system application is disabled in Version 1.')
        import psutil
        import win32gui
        import win32process
        import win32con
        exe = APPS[key][1].lower()
        if key == 'calculator':
            names = {'calculatorapp.exe', 'calculator.exe', 'calc.exe'}
        else:
            names = {exe}
        pids = set()
        for process in psutil.process_iter(['pid', 'name']):
            if (process.info['name'] or '').lower() in names:
                pids.add(process.info['pid'])
        windows = []
        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] in pids:
                windows.append(hwnd)
        win32gui.EnumWindows(collect, None)
        if not windows:
            return 'No visible windows were found for that application.'
        for hwnd in windows:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return 'Sent a normal close request. Check the app for any unsaved-work prompts; it has not been force-killed.'
