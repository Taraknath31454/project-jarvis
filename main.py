"""JARVIS entry point. All paths are relative to this project, not the shell."""
import argparse
from pathlib import Path
from core.config import load_config

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description="JARVIS personal desktop assistant")
    parser.add_argument('--cli', action='store_true', help='Use typed console commands')
    parser.add_argument('--setup', action='store_true', help='Generate settings without starting')
    args = parser.parse_args()
    config, created = load_config(ROOT)
    from core.diagnostics import configure
    configure(ROOT)
    if args.setup:
        print(f"Settings: {ROOT / 'config/settings.json'}")
        return
    from core.assistant import Assistant
    assistant = Assistant(ROOT, config)
    if args.cli:
        print('JARVIS ready. Type help, or goodbye to exit. Voice is off in CLI mode.')
        while True:
            try:
                result = assistant.execute(input('You > '))
            except (EOFError, KeyboardInterrupt):
                break
            print('JARVIS >', result.message)
            if result.exit:
                break
    else:
        from ui.desktop import Desktop
        Desktop(assistant, created).run()

if __name__ == '__main__':
    main()
