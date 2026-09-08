"""Bounded, nonblocking telemetry sampling. Unsupported values remain None."""
import os
import platform
from pathlib import Path
import shutil
import subprocess
import time
from core.diagnostics import failure
from services.network import byte_rates

class SystemMonitor:
    def __init__(self, root: Path):
        import psutil
        self.ps = psutil
        self.root = root
        self.previous = None
        self.previous_time = time.monotonic()
        self.first_cpu = True
        self.gpu_time, self.gpu = 0, None
        self.nvidia = shutil.which('nvidia-smi.exe')
        if not self.nvidia:
            for value in ('%SystemRoot%/System32/nvidia-smi.exe', '%ProgramFiles%/NVIDIA Corporation/NVSMI/nvidia-smi.exe'):
                candidate = Path(os.path.expandvars(value))
                if candidate.is_file():
                    self.nvidia = str(candidate)
                    break
        self.device = platform.node()
        self.os = f'{platform.system()} {platform.release()}'

    def sample(self) -> dict:
        data = {'cpu': None, 'ram': None, 'storage': None, 'battery': None, 'charging': None,
                'processes': None, 'uptime': None, 'download': None, 'upload': None,
                'device': self.device, 'os': self.os, 'gpu': None}
        operations = {'cpu': lambda: self.ps.cpu_percent(interval=None),
                      'ram': lambda: self.ps.virtual_memory().percent,
                      'storage': lambda: self.ps.disk_usage(self.root.anchor or str(self.root)).percent,
                      'processes': lambda: len(self.ps.pids()),
                      'uptime': lambda: max(0, time.time() - self.ps.boot_time())}
        for key, operation in operations.items():
            try:
                data[key] = operation()
            except Exception as exc:
                failure('monitor-' + key, exc)
        if self.first_cpu:
            data['cpu'], self.first_cpu = None, False
        try:
            battery = self.ps.sensors_battery()
            if battery:
                data.update(battery=battery.percent, charging=battery.power_plugged)
            now, current = time.monotonic(), self.ps.net_io_counters()
            data['download'], data['upload'] = byte_rates(self.previous, current, now - self.previous_time)
            self.previous, self.previous_time = current, now
        except Exception as exc:
            failure('monitor-battery-network', exc)
        if self.nvidia and time.monotonic() - self.gpu_time > 15:
            self.gpu_time = time.monotonic()
            try:
                result = subprocess.run([self.nvidia, '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=2, check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.gpu = float(result.stdout.strip().splitlines()[0])
            except Exception as exc:
                self.gpu = None
                failure('monitor-gpu', exc)
        data['gpu'] = self.gpu
        return data
