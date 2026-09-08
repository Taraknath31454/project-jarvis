# V2 baseline

Before edits: 17/17 unittest tests passed on the existing Windows Python 3.13 environment.
Source backup: `backups/jarvis-v1-source.zip` (includes existing settings; private, not committed).
User database, notes, reminders, screenshots, and model files are retained in place.

V1 uses Tkinter, with a Tk-thread event queue receiving results from command, microphone,
and TTS workers. Processing/Speaking are threading events; Listening follows microphone
availability. Idle is derived by the GUI. Errors were response messages, without a separate
visual state. V2 will add an explicit presentation state without changing execution authority.

Visual review: V1 has two large rectangular panels, a small three-ring emblem, and unused
space. The supplied reference suggests concentric technical rings, compact telemetry,
cyan linework and a central focal point. V2 will draw original geometry and keep JARVIS
branding, without copying reference logos, language, or wallpaper assets.

Decision: retain Tkinter and the existing services. Use lightweight Canvas widgets,
bounded histories, background telemetry/network workers, and queue-only UI updates.
