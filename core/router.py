"""Ordered, independently registered parsers; no free-form shell execution."""
import re
from core.models import Intent

class Router:
    def __init__(self):
        self.rules = []

    def register(self, pattern, action, transform=None):
        self.rules.append((re.compile(pattern, re.I), action, transform))

    def parse(self, text):
        text = text.strip().rstrip('.!?')
        text = re.sub(r'^(?:(?:could|can|would) you\s+)?(?:please\s+)?', '', text, flags=re.I)
        text = re.sub(r'\s+please$', '', text, flags=re.I)
        for pattern, action, transform in self.rules:
            match = pattern.fullmatch(text)
            if match:
                argument = transform(match) if transform else (match.groupdict().get('arg') or '')
                return Intent(action, argument.strip())
        return Intent('unknown')

def build_router():
    from commands import automation, personal, conversation, windows
    router = Router()
    for module in (windows, personal, automation, conversation):
        module.register(router)
    return router
