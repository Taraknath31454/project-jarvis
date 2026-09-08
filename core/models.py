from dataclasses import dataclass
from typing import Protocol

@dataclass
class Intent:
    action: str
    argument: str = ''

@dataclass
class Result:
    message: str
    action: str = 'unknown'
    success: bool = True
    exit: bool = False
    speak: bool = True

class Brain(Protocol):
    """Future language models may propose intents; execution still passes through safety."""
    def interpret(self, text: str) -> Intent | None: ...

# Future providers propose intents; they never receive direct Windows execution access.
AIProvider = Brain
