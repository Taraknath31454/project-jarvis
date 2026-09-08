"""Read-only integration diagnostics; does not record, speak, or control apps."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import load_config
from services.apps import Apps

def check(label, operation):
    try:
        print(f'{label}: {operation()}')
    except Exception as exc:
        print(f'{label}: unavailable ({type(exc).__name__})')

def main():
    root = Path(__file__).resolve().parents[1]
    config, _ = load_config(root)
    check('Chrome detected', lambda: bool(Apps(root, config).executable('chrome')))
    def audio():
        from pycaw.pycaw import AudioUtilities
        return round(AudioUtilities.GetSpeakers().EndpointVolume.GetMasterVolumeLevelScalar()*100)
    check('Audio endpoint volume (read only)', audio)
    def inputs():
        import sounddevice
        return sum(d['max_input_channels'] > 0 for d in sounddevice.query_devices())
    check('Available input device entries', inputs)
    def voices():
        import pyttsx3
        return len(pyttsx3.init().getProperty('voices'))
    check('Installed SAPI voices', voices)
    def model():
        import vosk
        vosk.SetLogLevel(-1)
        vosk.Model(str(root / config['microphone']['model_path']))
        return 'loaded successfully'
    check('Offline voice model', model)
    async def media():
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        return 'available' if manager else 'unavailable'
    with ThreadPoolExecutor(max_workers=1) as executor:
        check('Windows media session manager (worker thread)', lambda: executor.submit(lambda: asyncio.run(media())).result())

if __name__ == '__main__':
    main()
