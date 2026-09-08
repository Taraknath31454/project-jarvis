import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from datetime import datetime
from core.config import DEFAULTS, load_config, validate
from core.router import build_router
from core.assistant import Assistant
from services.apps import Apps, WINDOWS_TARGETS
from services.network import byte_rates
from services.monitor import SystemMonitor
from services.system import screenshot_name
from services.weather import fetch_weather
from services.desktop_integration import parse_hotkey, Startup
from ui.state import AssistantState

class V2Tests(unittest.TestCase):
    def test_old_config_migration_is_additive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'config').mkdir()
            original = {'user_name': 'Existing user', 'chrome_profiles': {'Work': 'Profile 3'},
                        'folder_aliases': {'my unity projects': 'D:/Existing'}}
            path = root/'config/settings.json'
            path.write_text(json.dumps(original), encoding='utf-8')
            config, created = load_config(root)
            self.assertFalse(created)
            self.assertEqual(config['chrome_profiles']['Work'], 'Profile 3')
            self.assertEqual(config['folder_aliases']['my unity projects'], 'D:/Existing')
            self.assertFalse(config['desktop']['start_with_windows'])
            self.assertEqual(json.loads(path.read_text()), original)

    def test_natural_variants(self):
        router = build_router()
        for command in ('Could you open Chrome?', 'Launch Chrome.', 'Start Chrome.', 'Open up Chrome.', 'Bring up Chrome.', 'Please open Chrome'):
            with self.subTest(command=command):
                intent = router.parse(command)
                self.assertEqual((intent.action, intent.argument), ('open', 'Chrome'))
        for command, action in [('battery status', 'battery'), ('show my reminders', 'list_reminders'),
                                ('show desktop', 'show_desktop'), ('minimize this window', 'minimize_window'),
                                ('switch to Chrome', 'switch_window'), ('toggle music', 'toggle_media')]:
            self.assertEqual(router.parse(command).action, action)

    def test_fixed_windows_targets(self):
        apps = Apps(Path('.'), copy.deepcopy(DEFAULTS))
        with patch('os.startfile', create=True) as start, patch('subprocess.Popen') as popen:
            apps.open('Bluetooth settings')
            start.assert_called_once_with('ms-settings:bluetooth')
            apps.open('Device Manager')
            self.assertEqual(popen.call_args.args[0][-1], 'devmgmt.msc')
            self.assertFalse(popen.call_args.kwargs['shell'])
            with self.assertRaises(ValueError): apps.open('cmd /c shutdown /s')

    def test_discovery_cache_revalidates(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = Path(temp)/'blender.exe'
            exe.write_bytes(b'test')
            apps = Apps(Path(temp), copy.deepcopy(DEFAULTS))
            with patch('shutil.which', return_value=str(exe)), patch.object(apps, 'discover_shortcut') as shortcuts:
                self.assertEqual(apps.executable('blender'), str(exe))
                self.assertEqual(apps.executable('blender'), str(exe))
                shortcuts.assert_not_called()
            exe.unlink()
            with patch('shutil.which', return_value=None), patch.object(apps, 'discover_shortcut', return_value=None), patch.dict('os.environ', {'ProgramFiles': temp}):
                self.assertIsNone(apps.executable('blender'))

    def test_configured_app_alias_uses_same_launcher(self):
        config = copy.deepcopy(DEFAULTS)
        config['app_aliases'] = {'browser': 'chrome'}
        apps = Apps(Path('.'), config)
        with patch.object(apps, 'chrome') as chrome:
            apps.open('browser')
            chrome.assert_called_once_with(profile=None)

    def test_rates_reset_and_missing_values(self):
        a = SimpleNamespace(bytes_recv=100, bytes_sent=20)
        b = SimpleNamespace(bytes_recv=1100, bytes_sent=220)
        self.assertEqual(byte_rates(a, b, 2), (500, 100))
        self.assertEqual(byte_rates(b, a, 2), (0, 0))
        self.assertEqual(byte_rates(None, b, 2), (None, None))
        self.assertEqual(byte_rates(a, b, 0), (None, None))

    def test_monitor_unavailable_is_not_faked(self):
        with patch('shutil.which', return_value=None), patch('pathlib.Path.is_file', return_value=False):
            monitor = SystemMonitor(Path.cwd())
        ps = Mock()
        for name in ('cpu_percent', 'virtual_memory', 'disk_usage', 'pids', 'boot_time', 'sensors_battery'):
            getattr(ps, name).side_effect = OSError('unavailable')
        monitor.ps = ps
        with patch('services.monitor.failure'):
            sample = monitor.sample()
        for key in ('cpu', 'ram', 'storage', 'battery', 'gpu', 'uptime', 'processes', 'download'):
            self.assertIsNone(sample[key])

    def test_weather_disabled_never_requests_network(self):
        with patch('urllib.request.urlopen') as request:
            result = fetch_weather(DEFAULTS['weather'])
            self.assertEqual(result['status'], 'DISABLED')
            request.assert_not_called()

    def test_weather_failure_is_offline(self):
        config = {'enabled': True, 'city': 'Test', 'latitude': 10, 'longitude': 20}
        with patch('urllib.request.urlopen', side_effect=OSError()), patch('services.weather.failure'):
            self.assertEqual(fetch_weather(config)['status'], 'OFFLINE')

    def test_hotkey_validation(self):
        self.assertEqual(parse_hotkey('ctrl+alt+j'), (0x4003, ord('J')))
        for key in ('ctrl+c', 'alt+f4', 'win+l', 'ctrl+alt+delete', 'ctrl+alt+j+extra', 'ctrl+ctrl+alt+j'):
            with self.subTest(key=key), self.assertRaises(ValueError): parse_hotkey(key)

    def test_startup_owns_only_one_registry_value(self):
        import winreg
        registry = Mock()
        registry.__enter__ = Mock(return_value=registry)
        registry.__exit__ = Mock(return_value=False)
        with patch.object(winreg, 'CreateKey', return_value=registry), patch.object(winreg, 'SetValueEx') as write, patch.object(winreg, 'DeleteValue') as delete:
            Startup.set_enabled(Path('C:/Project With Spaces'), True)
            self.assertEqual(write.call_args.args[1], Startup.NAME)
            self.assertIn('main.py', write.call_args.args[-1])
            Startup.set_enabled(Path('C:/Project With Spaces'), False)
            delete.assert_called_once_with(registry, Startup.NAME)

    def test_state_flow_and_error_expiry(self):
        state = AssistantState()
        self.assertEqual(state.resolve(now=100), 'Idle')
        state.listening_until = 110
        self.assertEqual(state.resolve(mic=True, now=101), 'Listening')
        self.assertEqual(state.resolve(processing=True, mic=True, now=102), 'Processing')
        self.assertEqual(state.resolve(speaking=True, mic=True, now=103), 'Speaking')
        self.assertEqual(state.resolve(mic=True, now=111), 'Idle')
        state.error_until = 120
        self.assertEqual(state.resolve(now=115), 'Error')
        self.assertEqual(state.resolve(now=121), 'Idle')
        self.assertEqual(state.resolve(offline=True), 'Offline')

    def test_screenshot_name(self):
        self.assertEqual(screenshot_name(datetime(2026, 9, 7, 6, 45, 12, 123456)), 'JARVIS_2026-09-07_06-45-12-123456.png')

    def test_new_file_open_blocks_executables(self):
        from services.system import System
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'bad.exe'
            path.write_bytes(b'test')
            with patch('os.startfile', create=True) as start, self.assertRaises(ValueError):
                System(Path(temp)).open_safe_file(path)
            start.assert_not_called()

if __name__ == '__main__': unittest.main()
