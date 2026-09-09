# JARVIS V2 — Personal AI Command Center

A modular Windows assistant with an original animated amber holographic HUD, real telemetry, typed commands, offline voice recognition, local Windows automation, spoken replies, notes and reminders. V2 retains V1's command services, data and confirmation boundary. No paid API, account, or cloud transcription is required.

## Launch the existing installation

```powershell
.\.venv\Scripts\python.exe main.py
```

Dependencies, including the optional tray library, and the offline voice model are already installed in this project. Existing `config/settings.json` values are preserved and merged with new defaults in memory. Saving Settings writes the complete validated configuration. Your notes and reminders remain in `data/jarvis.db`. A pre-upgrade source/configuration backup is in `backups/jarvis-v1-source.zip`.

See [V2 release notes and verification](docs/V2-RELEASE.md) for changed files, commands, test results, and limits.

## V2 dashboard

- Original vector AI core with state-dependent rotating rings, orbit markers and pulses. Real microphone amplitude drives the listening visualizer; speaking uses a state-driven animation, not an output-audio FFT.
- CPU, RAM, battery, system-drive storage, network byte rates, uptime, process count, device/OS, and optional NVIDIA GPU utilization. Unsupported or not-yet-sampled values display `N/A`. CPU and network need two samples before their first meaningful reading.
- CPU/RAM/network graph with a bounded 60-sample history. Default telemetry interval is 2 seconds and active animation is capped at 30 FPS; both are configurable. Idle uses at most 15 FPS and unchanged waveform/gauge frames are skipped. Animation work is reduced while minimized or in the tray.
- Quick launch, media controls, searchable help/palette, safe file-result overlay, notes viewer, upcoming reminders, recent activity and local notifications.
- Sectioned Settings: General, Voice, Applications, Chrome Profiles, Folders, Websites, System, Appearance, Weather and Privacy. Alias maps use small JSON editors; routine options use fields and toggles. Runtime changes apply after restart.
- Optional tray, close-to-tray, start-minimized and Windows startup. Startup stays **off** unless you explicitly enable it in Settings; it writes only JARVIS's current-user Windows `Run` registry value. Disabling the setting removes only that value. The path must remain valid if you move the project.
- Default global hotkey **Ctrl+Alt+J** brings JARVIS forward and focuses the terminal. Change/disable it in Settings → System. A conflict produces a notification and leaves the app usable.

| Shortcut | Action |
| --- | --- |
| Ctrl+Space | Focus command input while JARVIS is focused |
| Ctrl+K | Open command palette |
| Ctrl+Alt+J | Bring JARVIS forward globally (configurable) |
| F11 | Toggle fullscreen |
| Esc | Leave fullscreen; close the command palette when it has focus |
| Enter | Submit a typed command or selected palette command |

The main window retains native Windows decorations and resizing behavior, plus in-app minimize/maximize/close controls. Compact layouts are supported down to 1060×630 client pixels; verified sizes correspond to 1366×768, 1920×1080 and 2560×1440 displays.

### Optional weather

Weather is **disabled by default**. Set a city display name, latitude and longitude in Settings → Weather, then enable it. Only those coordinates are sent to [Open-Meteo](https://open-meteo.com/en/docs), which supplies current temperature, humidity and condition data. No API key is stored. Refresh defaults to 15 minutes; requests have a timeout. Connection failures show `WEATHER OFFLINE` and do not affect local commands. City text is a label, not automatic geocoding. No location is inferred from your device.

### Voice states

Enable the microphone and wait for **MICROPHONE: ACTIVE**. The core rests at **Idle** in silence, changes to **Listening** on input amplitude, then **Processing** while dispatching, **Speaking** during real TTS, and returns to **Idle** after output. This separates microphone availability from active listening. Error responses briefly mark the core amber. Local mode stays online even when the internet is unavailable.

Voice remains active when minimized or hidden to the tray if you enabled it. Close-to-tray requires tray support; if tray initialization fails, the window remains accessible. Use **Exit JARVIS** in the tray or “goodbye” to fully exit.

### Additional V2 commands

“Could you open Chrome?”, “Open up Chrome”, and “Bring up Chrome” share the original launcher. New commands include:

```text
Open Unity / Open Blender
Battery status
Open Device Manager / Open Control Panel / Open Recycle Bin
Open Bluetooth settings / Open Wi-Fi settings / Open display settings
Open sound settings / Open Windows Update / Open installed apps
Show desktop / Minimize all windows / Minimize this window
Switch to Chrome
System information / Network status
Show notes / Show my reminders
Open screenshots
```

`Unity` launches Unity Hub when found; configure an executable if you want a particular editor instead. Discovery checks executable configuration, PATH, registry, known install directories and validated Start Menu shortcut targets. Only executable targets are used; shortcut arguments are not executed. Discovered paths are cached in memory and revalidated before use. App aliases and quick launches are configurable.

Screenshots now use `JARVIS_YYYY-MM-DD_HH-MM-SS-microseconds.png`. **Screenshots ↗** opens their folder. File results have **Open** and **Open location** actions; executable/script files can only be revealed in Explorer. “Open result N” retains V1's reveal-only behavior.

The media panel sends the same commands as voice. Play/pause uses Windows' media-session toggle API. Current title/artist are shown only when a media session provides them. Device Manager/Windows settings may require Windows-owned elevation for changes; JARVIS does not bypass those prompts.

### Privacy and diagnostics in V2

Recent interactions are bounded and kept only in memory. Note, reminder, clipboard, search and unknown-command payloads are omitted from retained transcript entries. The current requested response may still display its content until replaced. **Clear history** clears both the in-memory transcript and existing activity table, not notes or reminders. Disable transcript retention in Settings → Privacy.

Developer diagnostics rotate under `logs/diagnostics.log`; they contain component names, exception types, and source locations, never raw input, exception messages or local variables. Network connectivity uses Windows' network status APIs without querying passwords or probing websites. NVIDIA monitoring is optional and uses a bounded `nvidia-smi` query; other GPUs display `N/A`.

## Start here

Use Windows 10/11, **64-bit Python 3.12 or 3.13**, and VS Code with Microsoft's Python extension. Install Python with Tcl/Tk support. Open this folder in VS Code, then run in its PowerShell terminal:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --setup
.\.venv\Scripts\python.exe tools/download_model.py
.\.venv\Scripts\python.exe main.py
```

Substitute `-3.12` if that is your installed version. Activation is optional; the commands above work without changing PowerShell execution policy. To activate, use `.\.venv\Scripts\Activate.ps1`. In VS Code, select `.venv\Scripts\python.exe` as the Python interpreter. F5 starts the desktop using the included launch configuration.

The one-time model download is approximately 40 MB from Alpha Cephei. Typed commands work without the model. After downloading, microphone recognition and speech synthesis work locally. Microphone capture starts only when you enable it from the window or tray. Windows startup is opt-in; audio is never recorded to disk.

For a console interface, run `python main.py --cli`. Console mode supports typed commands, but does not run microphone capture, TTS, or timed reminder notifications; use the desktop for those.

## Voice setup

1. In Windows Settings → Privacy & security → Microphone, enable microphone access and access for desktop apps.
2. Set your input device in Windows sound settings. For an explicit device, list available devices with `python -c "import sounddevice; print(sounddevice.query_devices())"` and set `microphone.device` to its numeric input index in JARVIS Settings.
3. Enable the microphone in JARVIS. Wait for **MICROPHONE: ACTIVE**, then say **“Jarvis, what time is it?”**
4. Wake detection gates locally recognized transcripts. It is not a dedicated acoustic wake-word engine. The default English model can misrecognize names or accents. It ignores other conversation until “Jarvis” is recognized, then accepts follow-up commands for 8 seconds. Set `follow_up_seconds` to `0` to require the wake word for every utterance.
5. Say a whole command after the wake word. For multi-turn notes or confirmations, say “Jarvis” again if the follow-up window has expired. Microphone input is suppressed during command processing and speech output to reduce self-triggering. Headphones help avoid speaker echo.

The optional offline backend is [Vosk](https://alphacephei.com/vosk/), with [sounddevice](https://python-sounddevice.readthedocs.io/) microphone capture. Alternative models from the [official model catalog](https://alphacephei.com/vosk/models) can be extracted under `models/` and selected with `microphone.model_path`. The included downloader installs the small US English model. No transcription is sent to a server.

## Configuration and first run

The first launch creates **`config/settings.json`**. Use the sectioned GUI **Settings** or edit the file directly. Validation errors are shown before saving. Restart JARVIS to apply changes. `core/config.py` defines defaults; existing V1 settings remain compatible.

| Setting | Purpose |
| --- | --- |
| `user_name`, `assistant_name` | Greeting name and assistant metadata (JARVIS) |
| `chrome_executable` | Optional absolute Chrome `.exe` path; otherwise PATH, registry, and standard environment-based install locations are checked |
| `chrome_profiles` | Spoken names mapped to Chrome profile directory names |
| `app_paths` | Canonical app IDs mapped to existing `.exe` files |
| `folder_aliases` | Folder names mapped to paths; `%USERPROFILE%` and `{project}` expand locally |
| `website_aliases` | Names mapped to full HTTPS/HTTP URLs |
| `microphone` | Device index, offline model path, wake word, follow-up window |
| `tts` | Enabled, rate, volume (0–1), optional installed SAPI voice ID |
| `safety` | Power commands disabled by default; confirmation lifetime |
| `search` | Search roots, maximum entries, maximum results |

### Chrome profiles

Open the desired Chrome profile manually, visit `chrome://version`, and inspect **Profile Path**. Use the final directory name, such as `Default` or `Profile 1`; do not copy the full path. Add your real mapping:

```json
"chrome_profiles": {
  "Tarak Lakshman": "Profile 1"
}
```

Then say **“Jarvis, open Chrome Tarak Lakshman.”** The mapping starts empty because your profile identity cannot safely be guessed. V1 validates profiles against Chrome's default `%LOCALAPPDATA%\Google\Chrome\User Data` location. Custom user-data roots require a future adapter change.

### Apps and folders

Canonical app IDs: `chrome`, `whatsapp`, `vscode`, `explorer`, `notepad`, `calculator`, `settings`, `spotify`, `steam`, `discord`, `task manager`, `unity`, `blender`. Spoken aliases include Google Chrome, VS Code, Visual Studio Code, File Explorer, and Whats App.

Paths are discovered through PATH, Windows App Paths registry entries, and standard environment-relative locations. Store/protocol applications use registered `whatsapp:`, `spotify:`, `steam:`, `discord:`, or `ms-settings:` handlers when an executable is not found. A successful launch request does not prove the app finished opening. Install the app or configure its canonical `app_paths` entry if detection fails. Custom executable paths must point to `.exe` files; shell scripts are not accepted.

Example customizations (merge into the generated JSON):

```json
"app_paths": {"vscode": "C:/Your/Install/Code.exe"},
"folder_aliases": {
  "my unity projects": "D:/Unity Projects",
  "project jarvis": "{project}",
  "downloads": "%USERPROFILE%/Downloads"
}
```

The Unity alias is intentionally unset until you supply its actual folder. For OneDrive-redirected Documents/Desktop, update folder aliases and `search.roots` to the real locations. File aliases allow PDF, text, and common image formats; executable files are not opened through file aliases.

## Commands

Typed commands can omit “Jarvis.”

| Feature | Examples |
| --- | --- |
| Apps | Open WhatsApp; open VS Code; open File Explorer; open Notepad; open Calculator; open Settings; open Spotify; open Steam; open Discord; open Task Manager |
| Chrome | Open Chrome; open Chrome Tarak Lakshman |
| Close | Close Chrome → confirm close chrome; close WhatsApp → confirm close whatsapp |
| Search | Search Google for reinforcement learning; search for Unity Rigidbody tutorial; Google weather in Vijayawada |
| Websites | Open YouTube; open Gmail; open GitHub; open ChatGPT; open Google; open Amazon |
| YouTube | Search YouTube for Unity character controller tutorial |
| Music | Play music; pause music; next song; previous song |
| Volume | Increase the volume; decrease volume; mute; unmute |
| System | Take a screenshot; show battery percentage; show current time; show current date |
| Lock | Lock computer → confirm lock |
| Folders | Open Downloads; open Documents; open my Unity projects; open Project JARVIS |
| Files | Find secondhand Unity project; find my PDF named Data Science notes; open result 1 |
| Reminders | Remind me in 20 minutes to study; remind me at 7 PM to call my friend; show reminders |
| Notes | Take a note, then dictate/type it; remember note: finish Unity assignment |
| Clipboard | Read clipboard; clear clipboard → confirm clear clipboard; save clipboard text as a note |
| Conversation | Hello Jarvis; how are you; thank you; goodbye; help |

Media commands use the current Windows media session via [Windows.Media.Control](https://learn.microsoft.com/en-us/uwp/api/windows.media.control). Open a player and select a track first. Some players do not expose a session or support every command. Play and pause are distinct actions; neither blindly toggles playback. Volume uses Windows Core Audio through [Pycaw](https://andremiras.github.io/pycaw/quickstart.html).

## Safety and privacy

- Voice text never becomes PowerShell/CMD code. Only registered handlers run, with fixed executable argument lists and URL-encoded search parameters.
- Closing an app, locking the computer, and clearing the clipboard require an exact, single-use confirmation within 20 seconds. A different command, cancellation, wrong confirmation, or expiry discards the request. Close requests target all visible windows belonging to that app using normal `WM_CLOSE`, preserving app-owned unsaved-work prompts. Nothing is force-killed. Closing Explorer, Settings, and Task Manager is disabled.
- Shutdown/restart are disabled by default. To enable them, explicitly set `safety.allow_power_commands` to `true`. Exact `confirm shutdown` / `confirm restart` is still required. Confirmation immediately invokes Windows power control without a force flag. Save your work before enabling or testing these commands.
- File search is limited to configured roots, at most 30,000 entries, 20 results, and roughly 8 seconds (a slow filesystem call can exceed the time budget). It avoids symlink/junction recursion. `open result N` only reveals a result in File Explorer; it never runs the matched file.
- History stores timestamps, canonical recognized command names, attempted actions, and success/failure. It intentionally omits raw speech, queries, filenames, note text, clipboard contents, and error details. History is capped at 500 entries. Sensitive payloads do not appear in the recent activity pane.
- Do not give JARVIS passwords or secrets. Obvious password/secret labels are rejected, but a string without context cannot reliably be classified as a secret. Notes, reminders, screenshots, and clipboard-to-note saves are intentional **unencrypted local content**. Clipboard read displays text only, without speaking or logging it. Generic logs never store arbitrary input. Search queries go to the search provider through Chrome.
- Your recognized command and reply remain on screen until replaced. Audio is not saved. The application does not send email/messages, require credentials, or run with administrator privileges.

## Local data and reminders

`data/jarvis.db` is SQLite storage for timestamped notes, reminders, and privacy-preserving command history. Screenshots go to `data/screenshots/`. Back up the database while JARVIS is closed to preserve notes/reminders. User configuration and runtime data are ignored by Git.

Keep the desktop app running for timely reminders. It does not wake a sleeping laptop or run a Windows background service. Overdue reminders appear after restart/resume. A reminder remains pending until its notification is dismissed, so an app crash does not silently lose it. Times use the laptop's local wall clock; V1 does not adjust saved reminders automatically across timezone changes. Relative units support integer seconds, minutes, hours, or days; absolute times support AM/PM or 24-hour `HH:MM`, with the next occurrence chosen.

Use **View notes** to read your most recent 100 notes. **View all** under Upcoming lists reminders and can dismiss selected entries. Recurrence and reminder editing are future extensions.

## Architecture

```text
main.py                 Desktop, CLI, and setup entry point
core/config.py          Defaults, validation, path expansion
core/router.py          Registered regex parsers → typed intents
core/assistant.py       Dispatch, safety boundary, multi-turn state
core/wake.py             Replaceable transcript wake gate
core/models.py          Intent/result types and future Brain protocol
commands/               Small parser registration modules
services/apps.py        App discovery, Chrome, websites, graceful closing
services/system.py      Audio, media, battery, screenshot, lock/power APIs
services/files.py       Bounded file search
services/storage.py     SQLite persistence and private activity history
services/reminders.py   Reminder time parsing
services/voice.py       Offline microphone worker and serialized TTS worker
ui/desktop.py           Tk interface; background results arrive through a queue
tools/download_model.py Official voice model setup
tests/                  Parsing, aliases, confirmations, persistence, privacy tests
```

To add a command, register its pattern in a small module's `register(router)`, include that module in `build_router`, and register the action handler in `Assistant.handlers`. Put integration details in a service. Every future AI intent must pass through this same executor and confirmation boundary. `Brain` defines an extension seam; V1 deliberately has no LLM backend. GUI widget mutations stay on the Tk main thread; commands, microphone capture, and TTS use separate workers.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q main.py core commands services ui tools tests
.\.venv\Scripts\python.exe tools/check_environment.py
```

Tests mock all risky automation. To smoke-test manually: launch the GUI, type “what time is it,” then try Notepad, a Google search, a one-minute reminder, and the microphone. Test Chrome profile mapping only after entering the real directory. Check media with your installed player. No automated test should shut down/restart/lock your PC or close your active apps.

`tools/check_environment.py` performs read-only checks of Chrome discovery, audio devices, SAPI voices, offline model loading, and the media-session API. `python tests/smoke_desktop.py` briefly opens the desktop with microphone and speech disabled, executes a typed time command, and saves `data/desktop-preview.png`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `python` opens Store or is denied | Use `py -3.13` or the project `.venv\Scripts\python.exe`; ensure a working Python installation |
| `No module named ...` | Install requirements using the same interpreter used to launch the app |
| GUI/Tk unavailable | Install official Python with Tcl/Tk; standard Windows Python includes it |
| Offline model missing | Run `tools/download_model.py`; `model_path` must point to the extracted directory containing `am/final.mdl` |
| Download blocked/offline | Download/extract the model manually from the official catalog on a connected device; typed commands still work |
| Mic unavailable | Check Windows privacy permissions, default input, device index, and whether another app holds exclusive access |
| Wake word/names misheard | Speak clearly, reduce noise, use a different English model, shorten aliases, or type the command |
| No spoken reply | Check `tts.enabled`, system output device/volume, installed Windows voices, and `voice_id`; clipboard and file results are display-only |
| Chrome/app not found | Configure its executable; ensure protocol-based apps are installed for this user |
| File/folder not found | Correct aliases/search roots, especially OneDrive folders; Unity's path starts unset |
| Settings invalid | Correct the JSON or rename `config/settings.json` so defaults can be regenerated; original invalid settings are not silently overwritten |
| Media unavailable | Start a track in a Windows media-session-compatible app before issuing media controls |
| Reminder not on time | Keep the GUI running and laptop awake; overdue reminders are delivered on next startup |

The framework handles unavailable optional integrations with a useful response. Actual microphone quality, app protocol registrations, installed Chrome profiles, and individual media-player behavior must be verified on your device.
