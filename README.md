# On The Spot

A deployable meeting copilot (MVP+) optimized for Apple Silicon.

## Included
- Realtime/local STT engine (`faster-whisper`, optional `mlx-whisper` on M-series)
- Desktop UI app (`desktop_app.py`, Tkinter)
- Context retrieval from local docs (`.md/.txt`)
- Talking-point suggestion engine
- **Save by default** session logs (`data/sessions/*.jsonl`)
- First-run setup wizard + persistent settings (`data/settings.json`)
- Live mic mode + one-click **Start Meeting Mode**

## Install

```bash
cd on-the-spot
python3 -m pip install --break-system-packages -r requirements.txt
```

Optional on Apple Silicon for best performance:

```bash
python3 -m pip install --break-system-packages mlx-whisper
```

## Run desktop app

```bash
cd on-the-spot
python3 desktop_app.py
```

In app:
- Choose mode: **Audio File** or **Live Mic**
- Hit **Start Meeting Mode**
- Settings persist automatically
- Use **Verify Invisibility** to run the built-in screen-share checklist

Overlay controls:
- Toggle **Overlay** in the app
- **Esc** = panic hide
- **Ctrl+Shift+O** = toggle overlay
- Click-through toggle included (best-effort in Tkinter)
- On macOS, optional `pyobjc` enables stronger native window behavior tuning (including sharing/capture exclusion hints)

## Run CLI

```bash
cd on-the-spot
python3 -m ots.main --audio /path/to/meeting.mp3 --kb ./kb --backend auto --model small
```

## Apple Silicon settings
- `--backend auto` prefers `mlx-whisper` if installed
- else falls back to `faster-whisper` int8 CPU path
- keep model at `small` for low latency; move to `base` if CPU constrained

## macOS packaging (signed/notarized-ready)

Build app bundle:
```bash
cd on-the-spot
./scripts/build_macos_app.sh
```

Build DMG:
```bash
./scripts/make_dmg.sh
```

Optional signing/notarization env vars:
- `CODESIGN_IDENTITY`
- `APPLE_ID`
- `APPLE_TEAM_ID`
- `APPLE_APP_PASSWORD`

## Notes
- Session saving is ON by default.
- This build now includes app packaging scripts and overlay hardening controls.
