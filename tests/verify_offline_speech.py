"""Decode generated test speech through the real offline model. No microphone recording."""
import json
from pathlib import Path
import sys
import tempfile
import wave
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import load_config
from core.wake import WakeGate
from core.router import build_router

def main():
    import pyttsx3
    from vosk import Model, KaldiRecognizer, SetLogLevel
    root = Path(__file__).resolve().parents[1]
    config, _ = load_config(root)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'generated-test-speech.wav'
        engine = pyttsx3.init()
        engine.setProperty('rate', 155)
        engine.save_to_file('Jarvis, what time is it?', str(path))
        engine.runAndWait()
        SetLogLevel(-1)
        model = Model(str(root/config['microphone']['model_path']))
        with wave.open(str(path), 'rb') as audio:
            assert audio.getnchannels() == 1 and audio.getsampwidth() == 2
            recognizer = KaldiRecognizer(model, audio.getframerate())
            texts = []
            while data := audio.readframes(4000):
                if recognizer.AcceptWaveform(data): texts.append(json.loads(recognizer.Result())['text'])
            texts.append(json.loads(recognizer.FinalResult())['text'])
        transcript = ' '.join(texts).strip()
        command = WakeGate().accept(transcript)
        assert command and build_router().parse(command).action == 'time', transcript
        print('PASS: generated speech -> real Vosk transcription -> wake word -> time intent.')
        print('No microphone audio was saved; generated test audio was removed.')

if __name__ == '__main__': main()
