# JARVIS V2 release notes

V2 upgrades the existing presentation and adds isolated services. No database migration or
replacement of notes/reminders was required. The original 17 tests are retained unchanged.
Tkinter remains the UI framework; no webview or heavyweight plotting dependency was added.

## Implemented

Original animated HUD core, real microphone-level waveform, circular telemetry gauges,
CPU/RAM/network graph, live clock/date, device information, optional weather, configurable
quick launches, command terminal, bounded private transcript, existing activity feed,
media controls/metadata, low-battery and connectivity notices, reminders and notes views,
safe file finder, searchable help/palette, sectioned settings, native window controls,
fullscreen, tray, global hotkey, and opt-in Windows startup.

All command buttons and palette entries route through `Desktop.submit` → `Assistant.execute`
→ existing services. File-result buttons select validated result indices through that router.
Windows opening targets are fixed URIs or argument lists. Shutdown/restart remain disabled
by default and require exact, expiring, single-use confirmation when enabled. No sign-out
shortcut or arbitrary shell execution was added.

## Files

| Area | New/updated files |
| --- | --- |
| HUD | `ui/desktop.py`, `ui/dashboard_layout.py`, `ui/theme.py`, `ui/state.py` |
| Widgets | `ui/widgets/ai_core.py`, `ui/widgets/telemetry.py` |
| Supporting windows | `ui/settings_window.py`, `ui/dialogs.py` |
| Telemetry/weather | `services/monitor.py`, `services/network.py`, `services/weather.py`, `services/dashboard.py` |
| Desktop lifecycle | `services/desktop_integration.py` |
| Existing services extended | `services/apps.py`, `services/system.py`, `services/storage.py`, `services/voice.py` |
| Commands/config | `core/config.py`, `core/router.py`, `core/assistant.py`, `core/wake.py`, `core/models.py`, `commands/automation.py`, `commands/conversation.py`, `commands/windows.py`, `commands/catalog.py` |
| Diagnostics | `core/diagnostics.py`, `main.py` |
| Tests | `tests/test_v2.py`, `tests/smoke_desktop.py`, `tests/verify_v2_gui.py`, `tests/verify_devices.py`, `tests/verify_offline_speech.py`, `tests/verify_entrypoint.py` |
| Setup/docs | `requirements.txt`, `README.md`, `docs/V2-BASELINE.md`, this file |

## Verification

- Baseline: 17 existing unit tests passing before edits.
- Expanded suite: 31 tests, including original tests plus migration preservation, deterministic
  aliases, fixed Windows commands, discovery caching, unavailable telemetry, rate resets,
  offline weather, hotkey validation, registry ownership, safe file opens, and state transitions.
- Real Tk rendering exercised at client sizes 1280×680, 1840×980, 2480×1340, corresponding
  to common 1366×768, 1920×1080, 2560×1440 displays. Window-only screenshots were inspected;
  a clipped microphone control was corrected. F11/Esc, help and Settings were exercised.
- GUI voice-event path with real Windows SAPI output verified exactly:
  **Idle → Listening → Processing → Speaking → Idle**.
- Actual microphone stream opened, delivered amplitude samples, and stopped cleanly.
  Recognized utterances were discarded in this hardware check; no audio was saved.
- Generated test speech decoded through real Vosk, then passed the wake gate and time-command
  router. This avoids falsely claiming a controlled recognition-accuracy test of the user's voice.
- Actual `RegisterHotKey` registration, a focus event delivered to that worker, unregistration,
  tray icon creation, Open JARVIS callback, and tray shutdown passed. No keys were synthesized.
- The real `main.py` entrypoint launch, rendering, and clean shutdown passed. Verification
  handles the Windows Store Python launcher's child interpreter without touching other apps.
  A settled four-second idle sample measured 15.2% of one CPU core, or 0.95% of this laptop's
  16 logical CPUs. This is a short local measurement, not a guarantee across devices/workloads.

Commands to repeat verification (the GUI/device scripts briefly open windows; the voice GUI
test speaks the time; microphone validation captures only in memory):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q main.py core commands services ui tools tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tests/smoke_desktop.py
.\.venv\Scripts\python.exe tests/verify_v2_gui.py
.\.venv\Scripts\python.exe tests/verify_devices.py
.\.venv\Scripts\python.exe tests/verify_offline_speech.py
.\.venv\Scripts\python.exe tests/verify_entrypoint.py
```

## Manual configuration and practical limits

- Map your actual Chrome profile directory and Unity-project folder. Existing mappings are
  preserved. Configure Unity/Blender executable paths if automatic discovery cannot find them.
- Weather needs explicitly entered latitude/longitude and a city display label; it defaults off.
- Tray/close-to-tray and Windows startup default off. Enable them only if desired. Startup
  configuration applies to this Windows user and does not require administrator access.
- Microphone defaults to the Windows input device. Change its index, wake word or model under
  Voice. Accuracy with your own voice, background noise and personal names still varies.
- 30 FPS is the default active animation cap; idle is capped at 15 FPS. 10–60 FPS and intensity are
  configurable. The speaking waveform is a visual state animation; the microphone uses real RMS.
- GPU utilization is NVIDIA-only where `nvidia-smi` is available. Network reachability reflects
  Windows' reported connectivity, which can lag captive portals or VPN changes.
- Start Menu discovery does not execute `.lnk` arguments. Multiple equally named installations
  may need a configured path. Windows can deny foreground focus switching.
- Calendar is the live local date display; external calendar account integration was not added.
  No fake calendar events, weather, media titles or telemetry are shown.
- Reminder delivery needs JARVIS running. Tray mode supports this, but it is not a Windows
  service and does not wake a sleeping laptop. Pending reminders reappear after restart.
- Configuration changes require restart. No paid or fake AI backend was introduced;
  `AIProvider` is an interface for future intent proposals, not authority to execute actions.

Launch: `.\.venv\Scripts\python.exe main.py`
