"""Deterministic Windows and device commands, shared by every input surface."""
def register(router):
    router.register(r'(?:minimize all windows|show desktop)', 'show_desktop')
    router.register(r'minimize (?:this|current) window', 'minimize_window')
    router.register(r'switch to (?P<arg>.+)', 'switch_window')
    router.register(r'(?:device information|system information|system status)', 'device_info')
    router.register(r'(?:network status|internet status|wifi status|wi-fi status)', 'network_info')
    router.register(r'open file result (?P<arg>\d+)', 'open_file_result')
    router.register(r'(?:show|view|list) (?:my )?notes', 'list_notes')
