import re
from datetime import datetime, timedelta

ONES = dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(), range(20)))
TENS = dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(), range(20, 100, 10)))

def spoken_number(value):
    if value.isdigit():
        return value
    words = value.lower().replace('-', ' ').split()
    if len(words) == 1:
        return str({**ONES, **TENS}.get(words[0], value))
    if len(words) == 2 and words[0] in TENS and words[1] in ONES and 0 < ONES[words[1]] < 10:
        return str(TENS[words[0]] + ONES[words[1]])
    return value

def parse_reminder(text, now=None):
    now = now or datetime.now()
    # Vosk often emits number words. Normalize only the scheduling prefix,
    # leaving the user's reminder content untouched.
    prefix, separator, content = text.partition(' to ')
    prefix = re.sub(r'^in (.+?) (seconds?|minutes?|hours?|days?)$',
                    lambda m: 'in ' + spoken_number(m[1]) + ' ' + m[2], prefix, flags=re.I)
    prefix = re.sub(r'^at (.+?)(\s*(?:a\.?\s*m\.?|p\.?\s*m\.?))?$',
                    lambda m: 'at ' + spoken_number(m[1].strip()) + (' ' + re.sub(r'[.\s]', '', m[2]) if m[2] else ''), prefix, flags=re.I)
    text = prefix + separator + content
    relative = re.fullmatch(r'in (\d+) (second|minute|hour|day)s? to (.+)', text, re.I)
    if relative:
        count = int(relative[1])
        seconds = count * {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}[relative[2].lower()]
        if not 0 < seconds <= 365 * 86400:
            raise ValueError('Choose a reminder between one second and 365 days away.')
        return now + timedelta(seconds=seconds), relative[3].strip()
    absolute = re.fullmatch(r'at (\d{1,2})(?::(\d{2}))?\s*(am|pm)? to (.+)', text, re.I)
    if absolute:
        hour, minute = int(absolute[1]), int(absolute[2] or 0)
        meridiem = (absolute[3] or '').lower()
        if minute > 59 or (meridiem and not 1 <= hour <= 12) or (not meridiem and hour > 23):
            raise ValueError('That time is invalid. Try at 7 PM or at 19:30.')
        if meridiem:
            hour = hour % 12 + (12 if meridiem == 'pm' else 0)
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due <= now:
            due += timedelta(days=1)
        return due, absolute[4].strip()
    raise ValueError('Try: remind me in 20 minutes to study, or remind me at 7 PM to call my friend.')
