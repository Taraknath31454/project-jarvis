"""Download the official small English Vosk model, with safe ZIP extraction."""
import os
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'vosk-model-small-en-us-0.15'
URL = f'https://alphacephei.com/vosk/models/{NAME}.zip'

def main():
    folder = ROOT / 'models'
    folder.mkdir(exist_ok=True)
    if (folder / NAME / 'am/final.mdl').is_file():
        print('Voice model is already installed.')
        return
    archive = folder / (NAME + '.zip.part')
    print(f'Downloading the approximately 40 MB English model from {URL}')
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, archive.open('wb') as target:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 150 * 1024 * 1024:
                    raise ValueError('Unexpectedly large download.')
                target.write(chunk)
        with zipfile.ZipFile(archive) as zipped:
            total = 0
            for info in zipped.infolist():
                destination = (folder / info.filename).resolve()
                if not destination.is_relative_to((folder / NAME).resolve()):
                    raise ValueError('The model archive contains an unsafe path.')
                total += info.file_size
                if total > 300 * 1024 * 1024:
                    raise ValueError('Unexpected model archive size.')
            zipped.extractall(folder)
        print('Installed. Start JARVIS and enable the microphone.')
    finally:
        if archive.exists():
            archive.unlink()

if __name__ == '__main__':
    main()
