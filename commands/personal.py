def register(router):
    router.register(r'remind me (?P<arg>.+)', 'reminder')
    router.register(r'(?:take a note|remember note|save note|note)(?:\s*:\s*|\s+)?(?P<arg>.*)', 'note')
    router.register(r'(?:show|list) (?:my )?reminders', 'list_reminders')
    router.register(r'read(?: (?:the|my))? clipboard', 'clipboard_read')
    router.register(r'clear(?: (?:the|my))? clipboard', 'clipboard_clear')
    router.register(r'save clipboard(?: text)? as (?:a )?note', 'clipboard_note')
    router.register(r'confirm (?P<arg>.+)', 'confirm')
    router.register(r'(?:cancel|no|never mind)', 'cancel')
