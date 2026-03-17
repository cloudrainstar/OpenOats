#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
APP_PATH="dist/OpenGranola.app"
DMG_PATH="dist/OpenGranola.dmg"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found at $APP_PATH"
  echo "Run ./scripts/build_swift_app.sh first"
  exit 1
fi

rm -f "$DMG_PATH"
hdiutil create -volname "OpenGranola" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

# Sign the DMG if a signing identity is available
if [[ -z "${CODESIGN_IDENTITY:-}" ]]; then
  CODESIGN_IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | sed 's/.*"\(.*\)"/\1/' || true)
  if [[ -z "$CODESIGN_IDENTITY" ]]; then
    CODESIGN_IDENTITY=$(security find-identity -v -p codesigning | grep "Apple Development" | head -1 | sed 's/.*"\(.*\)"/\1/' || true)
  fi
fi

if [[ -n "${CODESIGN_IDENTITY:-}" ]]; then
  echo "Signing DMG with: $CODESIGN_IDENTITY"
  codesign --force --sign "$CODESIGN_IDENTITY" "$DMG_PATH"
fi

echo "DMG created: $DMG_PATH"
