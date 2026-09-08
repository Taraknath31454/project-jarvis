"""Useful exception locations without raw input, local variables, or secret payloads."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import traceback

LOG = logging.getLogger('jarvis')

def configure(root: Path) -> None:
    if LOG.handlers:
        return
    (root / 'logs').mkdir(exist_ok=True)
    handler = RotatingFileHandler(root / 'logs/diagnostics.log', maxBytes=500_000, backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)

def failure(component: str, exc: BaseException) -> None:
    frames = traceback.extract_tb(exc.__traceback__)
    locations = ' > '.join(f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in frames)
    LOG.error('%s: %s at %s', component, type(exc).__name__, locations)
