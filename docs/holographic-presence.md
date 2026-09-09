# Holographic presence upgrade

The existing Tk desktop and service architecture remain in place. The amber/gold center follows the supplied 3D hologram blueprint: a spherical latitude/longitude mesh, breathing energy node, particle shell, tilted orbital trails, outer stabilization rings, an upper cap and a separate base emitter. No downloaded assets or new dependencies.

The mesh uses cached unit-sphere coordinates and a three-quarter camera. Short mesh and orbit segments, particles and the inner glow are sorted by depth each frame, so rear trails pass behind the energy node and foreground wireframe crosses in front. Near-side lines are brighter than the far hemisphere. Three independent orbital planes have luminous moving heads and fading trails. Transparent glow sprites are generated only on resize.

## State behavior

- Idle: breathing spherical shell, slow rotation and quiet particle drift.
- Listening: existing microphone RMS events drive smoothed expansion, brightness and resonance.
- Processing: contracted sphere, segmented mesh, accelerated rings and active scans.
- Speaking: real Speaker.busy timing gates synthetic syllable pulses. The core and audio bars share a clock/envelope; this is not measured TTS amplitude.
- Error: red-orange, gently unstable projection.
- Offline: dim degraded projection, supported by the presentation state API. Internet loss does not incorrectly disable the local assistant.
- Microphone off: slower, dimmer standby; typed processing and speech remain animated.

The layout includes a functional navigation rail, focused central projection, quick launch panel, telemetry, reminders, notes, media, transcript, activity and notification areas. Panel scan sweeps, voice-sensitive terminal/transcript lighting, microphone glow and activity fades use the existing animation loop. Button hover transitions remain intact. Compact layouts reduce gauge and transcript heights to preserve controls and the performance graph. Settings still control animation intensity and FPS; minimized/withdrawn windows skip rendering.

## Verification

Run from the project directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests\verify_v2_gui.py
.\.venv\Scripts\python.exe tests\verify_hologram.py
.\.venv\Scripts\python.exe tests\smoke_desktop.py
.\.venv\Scripts\python.exe tests\verify_devices.py
.\.venv\Scripts\python.exe tests\verify_offline_speech.py
.\.venv\Scripts\python.exe tests\verify_entrypoint.py
```

The hologram check uses temporary storage and no microphone capture. It checks moving geometry across seven modes, amplitude response, spherical geometry and depth shading, stable item count, zero-intensity clock behavior, four layouts, hidden-window pause/resume and callback errors. Window captures are saved in data/hologram-*.png. Existing GUI integration checks exercise the real SAPI busy state through the voice event queue, not acoustic recognition.

The main 1440×880 test view uses 282 persistent Canvas items (annotation count adapts on compact views). The final local verification measured 7.86 ms median / 11.56 ms p95 for Canvas updates and about 2.49% of total logical CPU capacity in the real-entrypoint idle sample. Update timing excludes deferred Tk painting; these are measurements on this machine, not hardware-independent guarantees. Bloom images are generated only on debounced resize. A full timer interval is left for event handling and painting between updates; hidden windows pause drawing.

Launch:

```powershell
.\.venv\Scripts\python.exe main.py
```
