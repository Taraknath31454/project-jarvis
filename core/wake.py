import re
import time

class WakeGate:
    """Local transcript gate, replaceable by a dedicated keyword spotter."""
    def __init__(self, word='jarvis', follow_up_seconds=8):
        self.pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.I)
        self.seconds = follow_up_seconds
        self.until = 0

    def accept(self, text, now=None):
        now = time.monotonic() if now is None else now
        match = self.pattern.search(text)
        if match:
            self.until = now + self.seconds
            after = text[match.end():].strip(' ,.!')
            before = text[:match.start()].strip(' ,.!')
            return after or (before.lower() if before.lower() in ('hello', 'hi', 'hey', 'thanks', 'thank you') else '')
        if now <= self.until and self.until > 0:
            self.until = now + self.seconds
            return text.strip()
        return None
