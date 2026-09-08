import re
import time
from core.models import Result
from core.router import build_router
from services.apps import Apps, canonical
from services.files import FileSearch
from services.storage import Storage
from services.system import System
from services.reminders import parse_reminder
from commands.conversation import responses
from core.diagnostics import failure

SENSITIVE = re.compile(r'\b(password|passcode|passwd|api[ _-]?key|secret|access token|otp|pin code)\b', re.I)

class Assistant:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.router = build_router()
        self.storage = Storage(root / 'data/jarvis.db')
        self.apps = Apps(root, config)
        self.system = System(root)
        self.files = FileSearch(root, config['search'])
        self.pending = None
        self.note_until = 0
        self.handlers = {
            'open': self.open, 'close': self.request_close,
            'google': lambda arg: self.apps.search('google', arg),
            'youtube': lambda arg: self.apps.search('youtube', arg),
            'find': self.files.find, 'note': self.note, 'reminder': self.reminder,
            'list_reminders': self.list_reminders, 'confirm': self.confirm, 'cancel': self.cancel,
            'clipboard_read': self.read_clipboard,
            'clipboard_note': self.clipboard_note,
            'clipboard_clear': lambda _: self.request('clear clipboard', 'clipboard_clear', ''),
            'show_desktop': lambda _: self.system.show_desktop(),
            'minimize_window': lambda _: self.system.minimize_window(),
            'switch_window': self.system.switch_window,
            'open_file_result': self.open_file_result,
            'list_notes': self.list_notes,
            'device_info': self.device_info, 'network_info': self.network_info,
        }
        for action in ('volume_up', 'volume_down', 'mute', 'unmute'):
            self.handlers[action] = lambda _, a=action: self.system.volume(a)
        for action in ('play', 'pause', 'next', 'previous', 'toggle_media'):
            self.handlers[action] = lambda _, a=action: self.system.media(a)
        for action in ('battery', 'screenshot'):
            self.handlers[action] = lambda _, a=action: getattr(self.system, a)()
        for action in ('lock', 'shutdown', 'restart'):
            self.handlers[action] = lambda _, a=action: self.request(a, a, '')

    def execute(self, text):
        action = 'unknown'
        try:
            if not isinstance(text, str) or len(text) > 4000 or '\x00' in text:
                raise ValueError('Please use a command shorter than 4000 characters.')
            if SENSITIVE.search(text):
                self.pending = None
                self.note_until = 0
                return Result('Please do not give JARVIS passwords or secrets. This input was not stored.', 'private_input', False, speak=False)
            name = re.escape(self.config['microphone']['wake_word'])
            text = re.sub(r'^\s*' + name + r'\b[\s,]*', '', text, flags=re.I).strip()
            text = re.sub(r'^(hello|hi|hey|thanks|thank you)\s+' + name + r'[.!]?$', r'\1', text, flags=re.I)
            if not text:
                text = 'hello core'
            intent = self.router.parse(text)
            action = intent.action
            if self.note_until > time.monotonic() and action != 'cancel':
                action = 'note'
                self.note_until = 0
                message = self.note(text)
            else:
                self.note_until = 0
                if action not in ('confirm', 'cancel'):
                    self.pending = None
                conversation = responses(self.config['user_name'])
                if action in conversation:
                    message = conversation[action]
                elif action in self.handlers:
                    confirmed_action = self.pending[1] if action == 'confirm' and self.pending else None
                    message = self.handlers[action](intent.argument)
                    if confirmed_action:
                        action = 'confirm_' + confirmed_action
                else:
                    message = 'I did not recognize that command. Type help for examples.'
            result = Result(message, action, action != 'unknown', exit=action == 'goodbye',
                            speak=action not in ('clipboard_read', 'find', 'list_reminders', 'list_notes'))
        except ValueError as exc:
            result = Result(str(exc), action, False)
        except ImportError:
            result = Result('A required package is missing. Install requirements.txt in your virtual environment.', action, False)
        except Exception as exc:
            failure(action, exc)
            result = Result('That action could not be completed. Check the app installation, permissions, or configured paths. Details are in the diagnostic log.', action, False)
        self.storage.history(result.action, result.success)
        return result

    def open(self, name):
        match = re.fullmatch(r'result (\d+)', name, re.I)
        if match:
            index = int(match[1]) - 1
            if not 0 <= index < len(self.files.results):
                raise ValueError('Run a file search first, then choose a listed result number.')
            return self.system.reveal(self.files.results[index])
        return self.apps.open(name)

    def open_file_result(self, index):
        index = int(index) - 1
        if not 0 <= index < len(self.files.results):
            raise ValueError('Run a file search and select a listed result first.')
        return self.system.open_safe_file(self.files.results[index])

    def list_notes(self, _):
        return '\n\n'.join(f'{created[:16]} — {text}' for _, created, text in self.storage.notes()) or 'No notes yet.'

    def device_info(self, _):
        import platform
        import psutil
        return f'{platform.node()}. {platform.system()} {platform.release()}. {len(psutil.pids())} active processes.'

    def network_info(self, _):
        from services.network import connection_status
        status = connection_status()
        return f'Internet: {status["internet"]}. Wi-Fi: {status["wifi"]}.'

    def request_close(self, name):
        key = canonical(name)
        if not key:
            raise ValueError('That application is not in the close allowlist.')
        if key in ('explorer', 'settings', 'task manager'):
            raise ValueError('Closing system applications is disabled in Version 1.')
        return self.request('close ' + key, 'close', key)

    def request(self, phrase, action, argument):
        if action in ('shutdown', 'restart') and not self.config['safety']['allow_power_commands']:
            raise ValueError('Shutdown and restart are disabled. Enable allow_power_commands in settings if you want to use them.')
        self.pending = (phrase, action, argument, time.monotonic() + self.config['safety']['confirmation_seconds'])
        warning = ' All visible windows for this app will receive a close request.' if action == 'close' else ''
        return f'Please confirm {phrase}.{warning} Type or say “confirm {phrase}” within {self.config["safety"]["confirmation_seconds"]} seconds, or cancel.'

    def confirm(self, phrase):
        pending, self.pending = self.pending, None
        if not pending or pending[3] < time.monotonic():
            raise ValueError('There is no active confirmation. Request the action again.')
        expected, action, argument, _ = pending
        if phrase.lower() != expected:
            raise ValueError('Confirmation did not match. The action was cancelled.')
        if action in ('shutdown', 'restart'):
            if not self.config['safety']['allow_power_commands']:
                raise ValueError('Power commands are disabled.')
            return self.system.power(action)
        if action == 'close':
            return self.apps.close(argument)
        if action == 'lock':
            return self.system.lock()
        if action == 'clipboard_clear':
            import pyperclip
            pyperclip.copy('')
            return 'Clipboard cleared.'
        raise ValueError('Unsupported confirmation action.')

    def cancel(self, _):
        self.pending = None
        self.note_until = 0
        return 'Cancelled.'

    def note(self, text):
        if not text:
            self.note_until = time.monotonic() + 30
            return 'What should I write? Give your note within 30 seconds, or say cancel.'
        if SENSITIVE.search(text):
            raise ValueError('Notes containing password or secret labels are not saved.')
        self.storage.note(text)
        return 'Your note has been saved locally.'

    def reminder(self, text):
        due, message = parse_reminder(text)
        self.storage.reminder(due, message)
        return f'Reminder saved for {due:%d %b at %I:%M %p}. Keep JARVIS running to receive it on time.'

    def list_reminders(self, _):
        pending = self.storage.pending()
        return '\n'.join(f'{due[:16].replace("T", " ")} — {text}' for _, due, text in pending) or 'No pending reminders.'

    def read_clipboard(self, _):
        import pyperclip
        text = pyperclip.paste()
        if SENSITIVE.search(text):
            return 'Clipboard may contain sensitive information and was not displayed.'
        return ('Clipboard (shown only, not spoken):\n' + text[:2000]) if text else 'The clipboard has no text.'

    def clipboard_note(self, _):
        import pyperclip
        text = pyperclip.paste()
        if not text:
            return 'The clipboard has no text.'
        if len(text) > 20000:
            raise ValueError('Clipboard is too large to save as a note (20,000 character limit).')
        return self.note(text)
