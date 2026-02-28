#!/usr/bin/env bash
set -euo pipefail

# Build unsigned/signed macOS .app for On The Spot
# Usage:
#   ./scripts/build_macos_app.sh
# Optional env:
#   CODESIGN_IDENTITY="Developer ID Application: ..."
#   APPLE_ID="name@example.com"
#   APPLE_TEAM_ID="TEAMID123"
#   APPLE_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"

cd "$(dirname "$0")/.."

python3 -m pip install --break-system-packages -q pyinstaller

rm -rf build dist

pyinstaller \
  --noconfirm \
  --windowed \
  --name "On The Spot" \
  --collect-all faster_whisper \
  --collect-all sklearn \
  --hidden-import sounddevice \
  --hidden-import soundfile \
  desktop_app.py

APP_PATH="dist/On The Spot.app"

if [[ -n "${CODESIGN_IDENTITY:-}" ]]; then
  echo "Signing app with identity: $CODESIGN_IDENTITY"
  codesign --deep --force --verify --verbose --options runtime --sign "$CODESIGN_IDENTITY" "$APP_PATH"
fi

if [[ -n "${APPLE_ID:-}" && -n "${APPLE_TEAM_ID:-}" && -n "${APPLE_APP_PASSWORD:-}" ]]; then
  ZIP_PATH="dist/OnTheSpot-mac.zip"
  ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"
  xcrun notarytool submit "$ZIP_PATH" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" \
    --wait
  xcrun stapler staple "$APP_PATH"
fi

echo "Build complete: $APP_PATH"
