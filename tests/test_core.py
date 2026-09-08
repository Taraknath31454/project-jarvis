import copy
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from core.assistant import Assistant
from core.config import DEFAULTS, load_config, validate
from core.router import build_router
from core.wake import WakeGate
from services.apps import canonical, Apps
from services.reminders import parse_reminder
from services.storage import Storage

class ParsingTests(unittest.TestCase):
    def test_commands(self):
        router = build_router()
        cases = {
            'open Google Chrome': ('open', 'Google Chrome'),
            'open Chrome Tarak Lakshman': ('open', 'Chrome Tarak Lakshman'),
            'search Google for reinforcement learning': ('google', 'reinforcement learning'),
            'Search for Unity Rigidbody tutorial': ('google', 'Unity Rigidbody tutorial'),
            'Google weather in Vijayawada': ('google', 'weather in Vijayawada'),
            'search YouTube for Unity character controller tutorial': ('youtube', 'Unity character controller tutorial'),
            'remember note: finish Unity assignment': ('note', 'finish Unity assignment'),
            'take a note': ('note', ''), 'increase the volume': ('volume_up', ''),
            'what time is it?': ('time', ''), 'pause music': ('pause', ''),
            'save clipboard text as a note': ('clipboard_note', ''),
            'close WhatsApp': ('close', 'WhatsApp'),
            'remind me at 7 PM to call my friend': ('reminder', 'at 7 PM to call my friend'),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                intent = router.parse(text)
                self.assertEqual((intent.action, intent.argument), expected)

    def test_aliases(self):
        for name, expected in [('Google Chrome', 'chrome'), ('VS Code', 'vscode'), ('File Explorer', 'explorer'),
                               ('WhatsApp', 'whatsapp'), ('Task Manager', 'task manager')]:
            self.assertEqual(canonical(name), expected)
        self.assertIsNone(canonical('cmd /c del *'))

    def test_wake_word_boundaries_and_timeout(self):
        gate = WakeGate()
        self.assertIsNone(gate.accept('open chrome', now=1))
        self.assertIsNone(gate.accept('jarvison open chrome', now=2))
        self.assertEqual(gate.accept('Jarvis, open Chrome', now=3), 'open Chrome')
        self.assertEqual(gate.accept('close chrome', now=4), 'close chrome')
        self.assertIsNone(gate.accept('open chrome', now=20))
        self.assertEqual(gate.accept('Hello Jarvis', now=21), 'hello')

    def test_reminder_times(self):
        now = datetime(2026, 9, 7, 20, 0)
        due, text = parse_reminder('in 20 minutes to study', now)
        self.assertEqual(due, now + timedelta(minutes=20))
        self.assertEqual(text, 'study')
        self.assertEqual(parse_reminder('at 7 PM to call', now)[0], datetime(2026, 9, 8, 19))
        self.assertEqual(parse_reminder('at 12 AM to call', now)[0], datetime(2026, 9, 8))
        self.assertEqual(parse_reminder('at 12 PM to call', now)[0], datetime(2026, 9, 8, 12))
        for text in ('in 0 minutes to study', 'in 999999999 days to study', 'at 25:00 to call', 'at 13 PM to call', 'at 7:99 PM to call'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_reminder(text, now)

    def test_spoken_reminder_numbers(self):
        now = datetime(2026, 9, 7, 12)
        self.assertEqual(parse_reminder('in twenty minutes to study', now)[0], now + timedelta(minutes=20))
        self.assertEqual(parse_reminder('in thirty five minutes to study', now)[0], now + timedelta(minutes=35))
        self.assertEqual(parse_reminder('at seven p m to call', now)[0], now.replace(hour=19))

class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config, _ = load_config(self.root)
        self.assistant = Assistant(self.root, self.config)
        self.assistant.apps = Mock()
        self.assistant.system = Mock()

    def tearDown(self):
        self.temp.cleanup()

    def test_power_disabled(self):
        result = self.assistant.execute('shutdown')
        self.assertFalse(result.success)
        self.assistant.system.power.assert_not_called()
        self.assertFalse(self.assistant.execute('confirm shutdown').success)

    def test_confirmation_exact_single_use(self):
        self.assistant.execute('close chrome')
        self.assistant.apps.close.assert_not_called()
        self.assertFalse(self.assistant.execute('confirm close discord').success)
        self.assistant.execute('close chrome')
        self.assistant.execute('confirm close chrome')
        self.assistant.apps.close.assert_called_once_with('chrome')
        self.assertFalse(self.assistant.execute('confirm close chrome').success)

    def test_confirmation_expires_cancels_and_intervening_command(self):
        with patch('core.assistant.time.monotonic', return_value=100):
            self.assistant.execute('lock computer')
        with patch('core.assistant.time.monotonic', return_value=121):
            self.assertFalse(self.assistant.execute('confirm lock').success)
        self.assistant.execute('lock computer')
        self.assistant.execute('cancel')
        self.assertFalse(self.assistant.execute('confirm lock').success)
        self.assistant.execute('lock computer')
        self.assistant.execute('what time is it')
        self.assertFalse(self.assistant.execute('confirm lock').success)
        self.assistant.system.lock.assert_not_called()

    def test_enabled_power_still_confirms(self):
        self.config['safety']['allow_power_commands'] = True
        self.assistant.execute('restart')
        self.assistant.system.power.assert_not_called()
        self.assistant.execute('confirm restart')
        self.assistant.system.power.assert_called_once_with('restart')

    def test_system_close_blocked(self):
        self.assertFalse(self.assistant.execute('close file explorer').success)
        self.assistant.apps.close.assert_not_called()

    def test_no_shell_for_unknown_input(self):
        with patch('subprocess.Popen') as popen:
            self.assertFalse(self.assistant.execute('powershell Remove-Item *').success)
            popen.assert_not_called()

    def test_note_followup_and_sensitive_rejection(self):
        self.assistant.execute('take a note')
        self.assistant.execute('finish Unity assignment')
        self.assertFalse(self.assistant.execute('remember note: password is abc').success)
        with self.assistant.storage.connect() as db:
            notes = db.execute('SELECT text FROM notes').fetchall()
        self.assertEqual(notes, [('finish Unity assignment',)])
        history = str(self.assistant.storage.recent())
        self.assertNotIn('finish Unity', history)
        self.assertNotIn('abc', history)

    def test_storage_restart_and_acknowledge(self):
        self.assistant.storage.reminder(datetime.now() - timedelta(seconds=2), 'study')
        restarted = Storage(self.root / 'data/jarvis.db')
        due = restarted.due()
        self.assertEqual(len(due), 1)
        self.assertEqual(len(restarted.due()), 1)
        restarted.acknowledge(due[0][0])
        self.assertEqual(restarted.due(), [])

    def test_missing_application_graceful(self):
        self.assistant.apps.open.side_effect = FileNotFoundError()
        result = self.assistant.execute('open chrome')
        self.assertFalse(result.success)
        self.assertIn('could not be completed', result.message)

    def test_file_search_only_reveals(self):
        folder = self.root / 'documents'
        folder.mkdir()
        (folder / 'Data Science notes.pdf').write_text('test')
        (folder / 'Data Science notes.exe').write_text('test')
        self.assistant.files.config['roots'] = [str(folder)]
        result = self.assistant.execute('find my PDF named Data Science notes')
        self.assertTrue(result.success)
        self.assertEqual(len(self.assistant.files.results), 1)
        self.assistant.system.reveal.assert_not_called()
        self.assistant.execute('open result 1')
        self.assistant.system.reveal.assert_called_once()

class ConfigurationTests(unittest.TestCase):
    def test_invalid_profiles_and_websites(self):
        config = copy.deepcopy(DEFAULTS)
        config['chrome_profiles']['test'] = '../outside'
        with self.assertRaises(ValueError):
            validate(config)
        config = copy.deepcopy(DEFAULTS)
        config['website_aliases']['bad'] = 'javascript:alert(1)'
        with self.assertRaises(ValueError):
            validate(config)

    def test_chrome_profile_and_urls(self):
        config = copy.deepcopy(DEFAULTS)
        config['chrome_profiles'] = {'Tarak Lakshman': 'Profile 1'}
        apps = Apps(Path('.'), config)
        with patch.object(apps, 'executable', return_value='chrome.exe'), patch('pathlib.Path.is_dir', return_value=True), patch('subprocess.Popen') as popen:
            apps.open('Chrome Tarak Lakshman')
            self.assertEqual(popen.call_args.args[0], ['chrome.exe', '--profile-directory=Profile 1'])
            apps.open('YouTube')
            self.assertEqual(popen.call_args.args[0][-1], 'https://www.youtube.com')
            apps.search('google', 'a & b; shutdown')
            self.assertIn('q=a+%26+b%3B+shutdown', popen.call_args.args[0][-1])
            with self.assertRaises(ValueError):
                apps.open('Chrome Unknown Person')

if __name__ == '__main__':
    unittest.main()
