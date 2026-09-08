import copy
import json
import os
from pathlib import Path
from urllib.parse import urlparse

DEFAULTS = {
    'user_name': 'Tara', 'assistant_name': 'JARVIS',
    'chrome_executable': '', 'chrome_profiles': {}, 'app_paths': {},
    'folder_aliases': {'downloads': '%USERPROFILE%/Downloads',
                       'documents': '%USERPROFILE%/Documents',
                       'my unity projects': '', 'project jarvis': '{project}'},
    'website_aliases': {'youtube': 'https://www.youtube.com', 'gmail': 'https://mail.google.com',
                        'github': 'https://github.com', 'chatgpt': 'https://chatgpt.com',
                        'google': 'https://www.google.com', 'amazon': 'https://www.amazon.in'},
    'microphone': {'device': None, 'model_path': 'models/vosk-model-small-en-us-0.15',
                   'wake_word': 'jarvis', 'follow_up_seconds': 8},
    'tts': {'enabled': True, 'rate': 180, 'volume': 0.8, 'voice_id': ''},
    'safety': {'allow_power_commands': False, 'confirmation_seconds': 20},
    'search': {'roots': ['%USERPROFILE%/Downloads', '%USERPROFILE%/Documents',
                          '%USERPROFILE%/Desktop'], 'max_results': 20, 'max_entries': 30000},
    'version': 2,
    'app_aliases': {},
    'dashboard': {'quick_launch': ['Chrome', 'WhatsApp', 'VS Code', 'Spotify', 'YouTube', 'File Explorer', 'Unity', 'Blender', 'Settings'],
                  'animation_intensity': 0.7, 'fps': 30, 'fullscreen': False},
    'weather': {'enabled': False, 'city': '', 'latitude': None, 'longitude': None, 'refresh_minutes': 15},
    'desktop': {'tray_enabled': False, 'close_to_tray': False, 'start_with_windows': False,
                'start_minimized': False, 'startup_sound': False, 'startup_greeting': False,
                'global_hotkey_enabled': True, 'global_hotkey': 'ctrl+alt+j'},
    'monitor': {'interval_seconds': 2, 'low_battery_warning': True, 'low_battery_percent': 20},
    'privacy': {'transcript_enabled': True, 'transcript_limit': 8},
}
DEFAULTS['folder_aliases'].update({'desktop': '%USERPROFILE%/Desktop', 'screenshots': '{project}/data/screenshots'})

def merge(defaults, custom):
    result = copy.deepcopy(defaults)
    for key, value in custom.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result

def validate(config):
    if not isinstance(config, dict):
        raise ValueError('Settings must be a JSON object.')
    for key in ('user_name', 'assistant_name', 'chrome_executable'):
        if not isinstance(config.get(key), str):
            raise ValueError(f'{key} must be a string.')
    for group in ('microphone', 'tts', 'safety', 'search', 'dashboard', 'weather', 'desktop', 'monitor', 'privacy'):
        if not isinstance(config.get(group), dict):
            raise ValueError(f'{group} must be a JSON object.')
    for group in ('chrome_profiles', 'app_paths', 'folder_aliases', 'website_aliases', 'app_aliases'):
        if not isinstance(config[group], dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in config[group].items()):
            raise ValueError(f'{group} must map names to strings.')
    for url in config['website_aliases'].values():
        if urlparse(url).scheme not in ('https', 'http') or not urlparse(url).netloc:
            raise ValueError('Website aliases must be complete HTTP(S) URLs.')
    for profile in config['chrome_profiles'].values():
        if not profile or any(c in profile for c in '/\\\x00') or profile in ('.', '..'):
            raise ValueError('Chrome profile values must be directory names, such as Default or Profile 1.')
    if not isinstance(config['safety']['allow_power_commands'], bool):
        raise ValueError('allow_power_commands must be true or false.')
    if not 1 <= float(config['safety']['confirmation_seconds']) <= 120:
        raise ValueError('confirmation_seconds must be between 1 and 120.')
    if not 0 <= float(config['microphone']['follow_up_seconds']) <= 30:
        raise ValueError('follow_up_seconds must be between 0 and 30.')
    if not 50 <= int(config['tts']['rate']) <= 400 or not 0 <= float(config['tts']['volume']) <= 1:
        raise ValueError('TTS rate must be 50–400 and volume 0–1.')
    if not isinstance(config['tts']['enabled'], bool) or not isinstance(config['tts']['voice_id'], str):
        raise ValueError('TTS enabled must be true/false and voice_id a string.')
    if not isinstance(config['microphone']['model_path'], str) or not isinstance(config['microphone']['wake_word'], str) or not config['microphone']['wake_word'].strip():
        raise ValueError('Microphone model_path and wake_word must be nonempty strings.')
    device = config['microphone']['device']
    if device is not None and (not isinstance(device, int) or isinstance(device, bool) or device < 0):
        raise ValueError('Microphone device must be null or a nonnegative integer index.')
    search = config['search']
    if not isinstance(search['roots'], list) or not all(isinstance(p, str) for p in search['roots']):
        raise ValueError('Search roots must be a list of paths.')
    if not 1 <= int(search['max_results']) <= 100 or not 1 <= int(search['max_entries']) <= 100000:
        raise ValueError('Search limits must be 1–100 results and 1–100000 entries.')
    dash = config['dashboard']
    if not isinstance(dash['quick_launch'], list) or not all(isinstance(s, str) and 0 < len(s) <= 40 for s in dash['quick_launch']) or len(dash['quick_launch']) > 12:
        raise ValueError('Quick launch must contain at most 12 short app/website/folder names.')
    if not 0 <= float(dash['animation_intensity']) <= 1 or not 10 <= int(dash['fps']) <= 60:
        raise ValueError('Animation intensity must be 0–1 and FPS 10–60.')
    for group, keys in {'dashboard': ['fullscreen'], 'weather': ['enabled'],
                        'desktop': ['tray_enabled', 'close_to_tray', 'start_with_windows', 'start_minimized', 'startup_sound', 'startup_greeting', 'global_hotkey_enabled'],
                        'monitor': ['low_battery_warning'], 'privacy': ['transcript_enabled']}.items():
        if any(not isinstance(config[group][k], bool) for k in keys):
            raise ValueError(f'{group} toggle values must be true or false.')
    if config['desktop']['close_to_tray'] and not config['desktop']['tray_enabled']:
        raise ValueError('Enable the system tray before enabling close-to-tray.')
    if not 1 <= int(config['privacy']['transcript_limit']) <= 30:
        raise ValueError('Transcript limit must be 1–30.')
    if not 1 <= float(config['monitor']['interval_seconds']) <= 30 or not 5 <= int(config['monitor']['low_battery_percent']) <= 50:
        raise ValueError('Monitor interval must be 1–30 seconds, low battery 5–50 percent.')
    weather = config['weather']
    if not isinstance(weather['city'], str) or not 5 <= int(weather['refresh_minutes']) <= 120:
        raise ValueError('Weather requires a city label and refresh interval of 5–120 minutes.')
    for key, limit in [('latitude', 90), ('longitude', 180)]:
        if weather[key] is not None and not -limit <= float(weather[key]) <= limit:
            raise ValueError(f'Invalid weather {key}.')
    if weather['enabled'] and (weather['latitude'] is None or weather['longitude'] is None):
        raise ValueError('Set weather latitude and longitude before enabling weather.')
    from services.desktop_integration import parse_hotkey
    parse_hotkey(config['desktop']['global_hotkey'])
    return config

def save_config(root, config):
    """Atomic save; old settings remain untouched if validation fails."""
    validate(config)
    path = root / 'config/settings.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(config, indent=2), encoding='utf-8')
    temp.replace(path)

def load_config(root):
    for folder in ('config', 'data', 'logs', 'models'):
        (root / folder).mkdir(exist_ok=True)
    path = root / 'config/settings.json'
    created = not path.exists()
    if created:
        path.write_text(json.dumps(DEFAULTS, indent=2), encoding='utf-8')
    try:
        custom = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(custom, dict):
            raise ValueError('Settings must be a JSON object.')
        return validate(merge(DEFAULTS, custom)), created
    except (ValueError, TypeError, KeyError) as exc:
        raise SystemExit(f'Invalid settings in {path}: {exc}. Fix the file or rename it to regenerate defaults.') from exc

def expand_path(value, root):
    return Path(os.path.expandvars(value.replace('{project}', str(root)))).expanduser()
