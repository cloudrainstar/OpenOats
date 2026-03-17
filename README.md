# OpenGranola

OpenGranola is a macOS meeting copilot for live conversations. It listens to your mic and the other side of the call, transcribes both streams in real time, searches your notes, and surfaces grounded talking points while the conversation is happening.

## What It Does

- Captures your microphone and system audio separately during a call
- Transcribes speech locally on-device with FluidAudio, Parakeet-TDT, and VAD
- Indexes local `.md` and `.txt` knowledge-base files
- Retrieves relevant context with Voyage AI embeddings and reranking
- Generates selective, evidence-backed suggestions with OpenRouter
- Shows a live transcript and a compact suggestions pane
- Saves plain-text transcripts and structured session logs locally
- Hides app windows from screen sharing by default

## How It Works

OpenGranola is local-first, but not fully offline:

- Transcription runs locally on your Mac
- Knowledge-base chunks are sent to Voyage AI for embeddings and reranking
- Recent conversation context and retrieved KB evidence are sent to OpenRouter to generate suggestions
- API keys are stored in Keychain; other app settings are stored locally in `UserDefaults`

## Requirements

- Apple Silicon Mac
- macOS 26+
- Xcode 26 / Swift 6.2 toolchain
- An OpenRouter API key for suggestions
- A Voyage AI API key for knowledge-base indexing and retrieval

## Quick Start

1. Build and install the app:

   ```bash
   ./scripts/build_swift_app.sh
   ```

2. Launch `/Applications/OpenGranola.app`.

3. Grant permissions when macOS prompts for them:
   - Microphone access
   - Screen capture / system audio access

4. Open Settings with `Cmd+,` and configure:
   - `Voyage AI` API key
   - `OpenRouter` API key
   - Model name
   - Microphone input
   - Transcription locale
   - Optional knowledge-base folder

5. Click `Idle` to start a session.

The first live run downloads the local ASR model, which is roughly 600 MB.

## Build

```bash
./scripts/build_swift_app.sh
```

This script:

- builds the Swift package in release mode
- creates `dist/OpenGranola.app`
- signs the app if a signing identity is available
- optionally notarizes it if Apple credentials are present
- installs the app to `/Applications/OpenGranola.app`

Optional environment variables for signing and notarization:

- `CODESIGN_IDENTITY`
- `APPLE_ID`
- `APPLE_TEAM_ID`
- `APPLE_APP_PASSWORD`

For a package-only build during development:

```bash
cd OpenGranola
swift build -c debug
```

## Using the App

- The top bar shows KB indexing status and lets you choose a knowledge-base folder
- The main pane shows suggestion cards grounded in retrieved KB sources
- The transcript pane shows both speakers and lets you copy the finalized transcript
- The bottom control bar starts and stops live capture and shows mic activity
- Suggestions only appear when the app decides the current moment is worth surfacing and it has strong enough KB evidence

## Knowledge Base

- Point the app at a folder containing `.md` or `.txt` files
- Files are chunked locally and cached after embedding
- The app re-indexes when the folder or Voyage API key changes
- KB cache is stored at `~/Library/Application Support/OpenGranola/kb_cache.json`

## Permissions And Local Data

- Microphone permission is required to capture your side of the conversation
- Screen capture permission is required to capture system audio from the other side of the call
- Plain-text transcripts are saved to `~/Documents/OpenGranola/`
- Structured JSONL session logs are saved to `~/Library/Application Support/OpenGranola/sessions/`
- `Hide from screen sharing` is enabled by default and can be changed in Settings

## Packaging

To build a DMG after building the app:

```bash
./scripts/make_dmg.sh
```

The GitHub release workflow uses the same Swift build script and then packages `dist/OpenGranola.dmg`.

## Repo Layout

- `OpenGranola/` — SwiftUI app source (Swift Package)
- `scripts/build_swift_app.sh` — build, sign, and install
- `scripts/make_dmg.sh` — package DMG for distribution
