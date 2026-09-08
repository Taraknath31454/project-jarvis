"""One searchable command catalog for help and the command palette."""
CATEGORIES = {
    'Applications': ['Open Chrome', 'Open WhatsApp', 'Open VS Code', 'Open Unity', 'Open Blender', 'Close Chrome'],
    'Browser': ['Open YouTube', 'Open Gmail', 'Open Chrome Tarak Lakshman'],
    'Files': ['Open Downloads', 'Open Documents', 'Open Desktop', 'Open screenshots', 'Find Data Science notes', 'Open result 1'],
    'System': ['Battery status', 'Take a screenshot', 'Open Task Manager', 'Open Device Manager', 'Open Control Panel', 'Open Recycle Bin', 'Open Bluetooth settings', 'Open Wi-Fi settings', 'Open display settings', 'Open sound settings', 'Open Windows Update', 'Open installed apps', 'Lock computer'],
    'Media': ['Open Spotify', 'Play music', 'Pause music', 'Next song', 'Previous song', 'Increase volume', 'Decrease volume', 'Mute', 'Unmute'],
    'Reminders': ['Remind me in 20 minutes to study', 'Remind me at 7 PM to call my friend', 'Show my reminders'],
    'Notes': ['Take a note', 'Remember note: finish Unity assignment', 'Show notes', 'Save clipboard text as a note'],
    'Search': ['Search Google for Unity animation', 'Search YouTube for Unity tutorials', 'Find my Unity project'],
    'Window management': ['Minimize this window', 'Minimize all windows', 'Show desktop', 'Switch to Chrome'],
    'Device information': ['System information', 'Network status', 'Battery status'],
    'Conversation': ['Hello Jarvis', 'What time is it?', 'Show current date', 'Thanks Jarvis', 'Goodbye'],
}

def search_commands(query: str, category: str = 'All') -> list[str]:
    groups = CATEGORIES.values() if category == 'All' else [CATEGORIES.get(category, [])]
    return list(dict.fromkeys(command for group in groups for command in group if query.lower() in command.lower()))
