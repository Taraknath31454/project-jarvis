"""Background-only dashboard data. Tk is never accessed from these workers."""
import threading
import time
from services.monitor import SystemMonitor
from services.network import connection_status
from services.weather import fetch_weather
from core.diagnostics import failure

class DashboardFeed:
    def __init__(self, assistant, events):
        self.assistant, self.events = assistant, events
        self.stop_event = threading.Event()
        self.threads = []

    def start(self):
        for name, target in [('telemetry', self._telemetry), ('network', self._network), ('weather', self._weather), ('local-data', self._local)]:
            thread = threading.Thread(target=target, daemon=True, name='jarvis-' + name)
            self.threads.append(thread)
            thread.start()

    def _telemetry(self):
        try:
            monitor = SystemMonitor(self.assistant.root)
            while not self.stop_event.is_set():
                self.events.put(('telemetry', monitor.sample()))
                self.stop_event.wait(self.assistant.config['monitor']['interval_seconds'])
        except Exception as exc:
            failure('telemetry-worker', exc)
            self.events.put(('notification', 'System monitoring unavailable. Commands remain available.'))

    def _network(self):
        while not self.stop_event.is_set():
            self.events.put(('network', connection_status()))
            self.stop_event.wait(20)

    def _weather(self):
        while not self.stop_event.is_set():
            self.events.put(('weather', fetch_weather(self.assistant.config['weather'])))
            self.stop_event.wait(self.assistant.config['weather']['refresh_minutes'] * 60)

    def _local(self):
        media_time = 0
        while not self.stop_event.is_set():
            try:
                storage = self.assistant.storage
                self.events.put(('local_data', {'reminders': storage.pending(), 'due': storage.due(), 'history': storage.recent()}))
                if time.monotonic() - media_time >= 10:
                    media_time = time.monotonic()
                    self.events.put(('media', self.assistant.system.media_metadata()))
            except Exception as exc:
                failure('dashboard-local-data', exc)
            self.stop_event.wait(2)

    def stop(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=.2)
