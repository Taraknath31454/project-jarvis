"""Presentation state only; never authorizes a command."""
import time

class AssistantState:
    def __init__(self):
        self.error_until = 0.0
        self.listening_until = 0.0
        self.level = 0.0

    def error(self):
        self.error_until = time.monotonic() + 3

    def audio(self, level):
        self.level = level
        if level > .035:
            self.listening_until = time.monotonic() + .5

    def resolve(self, processing=False, speaking=False, mic=False, offline=False, now=None):
        now = time.monotonic() if now is None else now
        if offline: return 'Offline'
        if processing: return 'Processing'
        if speaking: return 'Speaking'
        if now < self.error_until: return 'Error'
        if mic and now < self.listening_until: return 'Listening'
        return 'Idle'
