"""Offline microphone and serialized SAPI speech, isolated from Tk's main thread."""
import json
import queue
import threading
import time
from array import array
from core.diagnostics import failure
from core.config import expand_path
from core.wake import WakeGate

class Speaker:
    def __init__(self, config, events):
        self.config, self.events = config, events
        self.busy = threading.Event()
        self.queue = queue.Queue()
        threading.Thread(target=self._run, daemon=True, name='jarvis-tts').start()

    def say(self, text):
        if self.config['enabled']:
            self.busy.set()
            self.queue.put(text)

    def _run(self):
        engine = None
        while True:
            text = self.queue.get()
            if text is None:
                return
            self.busy.set()
            self.events.put(('status', 'Speaking'))
            try:
                if engine is None:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', self.config['rate'])
                    engine.setProperty('volume', self.config['volume'])
                    if self.config['voice_id']:
                        engine.setProperty('voice', self.config['voice_id'])
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                failure('tts', exc)
                self.events.put(('notice', 'Speech output is unavailable. Check TTS packages and Windows voices; typed commands still work.'))
                engine = None
            finally:
                if self.queue.empty():
                    self.busy.clear()
                self.events.put(('status', 'Idle'))

class Microphone:
    def __init__(self, root, config, events, speaking, processing):
        self.root, self.config, self.events = root, config, events
        self.speaking, self.processing = speaking, processing
        self.stop_event = threading.Event()
        self.thread = None
        self.gate = WakeGate(config['wake_word'], config['follow_up_seconds'])
        self.last_level = 0

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._listen, daemon=True, name='jarvis-mic')
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _listen(self):
        try:
            model_path = expand_path(self.config['model_path'], self.root)
            if not model_path.is_absolute():
                model_path = self.root / model_path
            if not (model_path / 'am/final.mdl').is_file():
                raise ValueError('Offline voice model missing. Run python tools/download_model.py, then enable the microphone.')
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            self.events.put(('status', 'Loading voice model'))
            model = Model(str(model_path))
            rate = int(sd.query_devices(self.config['device'], 'input')['default_samplerate'])
            recognizer = KaldiRecognizer(model, rate)
            audio = queue.Queue(maxsize=16)
            def callback(data, frames, time_info, status):
                if self.speaking.is_set() or self.processing.is_set():
                    return
                try:
                    audio.put_nowait(bytes(data))
                except queue.Full:
                    pass
            with sd.RawInputStream(samplerate=rate, blocksize=4000, device=self.config['device'],
                                   dtype='int16', channels=1, callback=callback):
                self.events.put(('mic', True))
                self.events.put(('status', 'Listening'))
                while not self.stop_event.is_set():
                    if self.speaking.is_set() or self.processing.is_set():
                        recognizer.Reset()
                        while not audio.empty():
                            try:
                                audio.get_nowait()
                            except queue.Empty:
                                break
                        self.stop_event.wait(0.1)
                        continue
                    try:
                        chunk = audio.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if time.monotonic() - self.last_level > 0.08:
                        self.last_level = time.monotonic()
                        samples = array('h', chunk)
                        level = (sum(v * v for v in samples) / max(1, len(samples))) ** 0.5 / 32768
                        self.events.put(('audio_level', min(1.0, level * 8)))
                    if recognizer.AcceptWaveform(chunk):
                        text = json.loads(recognizer.Result()).get('text', '')
                        if text:
                            accepted = self.gate.accept(text)
                            if accepted is not None:
                                self.events.put(('voice', accepted))
        except ValueError as exc:
            self.events.put(('notice', str(exc)))
        except Exception as exc:
            failure('microphone', exc)
            self.events.put(('notice', 'Microphone unavailable. Check the input device and Windows microphone privacy permissions.'))
        finally:
            self.events.put(('mic', False))
            self.events.put(('status', 'Idle'))
