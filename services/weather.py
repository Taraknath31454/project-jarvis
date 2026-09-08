"""Optional Open-Meteo current conditions; only explicitly configured coordinates leave the device."""
import json
import urllib.request
from urllib.parse import urlencode
from core.diagnostics import failure

def condition(code: int) -> str:
    if code == 0: return 'Clear sky'
    if code in (1, 2, 3): return 'Partly cloudy' if code < 3 else 'Overcast'
    if code in (45, 48): return 'Fog'
    if code in (51, 53, 55, 56, 57): return 'Drizzle'
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return 'Rain'
    if code in (71, 73, 75, 77, 85, 86): return 'Snow'
    if code in (95, 96, 99): return 'Thunderstorm'
    return 'Conditions unavailable'

def fetch_weather(config: dict) -> dict:
    if not config['enabled']:
        return {'status': 'DISABLED', 'city': config['city']}
    params = {'latitude': config['latitude'], 'longitude': config['longitude'],
              'current': 'temperature_2m,relative_humidity_2m,weather_code', 'timezone': 'auto'}
    try:
        with urllib.request.urlopen('https://api.open-meteo.com/v1/forecast?' + urlencode(params), timeout=7) as response:
            raw = json.loads(response.read(250_000))
        current = raw['current']
        return {'status': 'ONLINE', 'city': config['city'] or 'Configured location',
                'temperature': float(current['temperature_2m']), 'humidity': float(current['relative_humidity_2m']),
                'condition': condition(current['weather_code']), 'time': current['time']}
    except Exception as exc:
        failure('weather', exc)
        return {'status': 'OFFLINE', 'city': config['city']}
