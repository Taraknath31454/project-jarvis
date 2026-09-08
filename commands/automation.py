def register(router):
    router.register(r'(?:search (?:google )?for|google) (?P<arg>.+)', 'google')
    router.register(r'search youtube for (?P<arg>.+)', 'youtube')
    router.register(r'(?:open(?: up)?|bring up|launch|start) (?P<arg>.+)', 'open')
    router.register(r'(?:close|quit) (?P<arg>.+)', 'close')
    router.register(r'(?:find|find my) (?P<arg>.+)', 'find')
    for pattern, action in {
        r'(?:increase|raise|turn up) (?:the )?volume': 'volume_up',
        r'(?:decrease|lower|turn down) (?:the )?volume': 'volume_down',
        r'mute(?: (?:the )?(?:volume|sound))?': 'mute',
        r'unmute(?: (?:the )?(?:volume|sound))?': 'unmute',
        r'(?:take (?:a )?)?screenshot': 'screenshot',
        r'(?:show |what is |check )?(?:the )?battery(?: percentage| level| status)?': 'battery',
        r'lock(?: (?:the |my )?(?:computer|pc|laptop))?': 'lock',
        r'(?:shutdown|shut down)(?: (?:the |my )?(?:computer|pc|laptop))?': 'shutdown',
        r'restart(?: (?:the |my )?(?:computer|pc|laptop))?': 'restart',
        r'play(?: music)?': 'play', r'pause(?: music)?': 'pause',
        r'next(?: song| track)?': 'next', r'previous(?: song| track)?': 'previous',
        r'(?:play/pause|toggle music)': 'toggle_media',
    }.items():
        router.register(pattern, action)
