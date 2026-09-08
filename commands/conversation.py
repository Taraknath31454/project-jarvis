from datetime import datetime

def register(router):
    router.register(r'hello core', 'ready')
    for pattern, action in {
        r'(?:hello|hi|hey)': 'hello', r'how are you': 'wellbeing',
        r'(?:what(?: is|\x27s) (?:the )?(?:current )?time|what time is it|(?:show )?(?:the )?(?:current )?time)': 'time',
        r'(?:what(?: is|\x27s) (?:the )?(?:current )?date|(?:show )?(?:the )?(?:current )?date|what day is it)': 'date',
        r'(?:thank you|thanks)': 'thanks', r'(?:goodbye|exit jarvis|bye)': 'goodbye',
        r'(?:help|what can you do)': 'help',
    }.items():
        router.register(pattern, action)

def responses(name):
    return {'ready': 'At your service.', 'hello': f'Hello, {name}. At your service.', 'wellbeing': 'All systems ready. How can I help?',
            'time': datetime.now().strftime('It is %I:%M %p.'),
            'date': datetime.now().strftime('Today is %A, %d %B %Y.'),
            'thanks': 'Anytime.', 'goodbye': 'Goodbye. See you soon.',
            'help': 'Try: open Chrome, search Google for Unity, take a screenshot, remind me in 20 minutes to study, '
                    'take a note, show reminders, find Data Science notes, or what time is it. '
                    'For voice, say Jarvis first. Close, lock, and clear clipboard ask for confirmation.'}
