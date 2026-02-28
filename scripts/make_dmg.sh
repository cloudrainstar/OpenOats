#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
APP_PATH="dist/On The Spot.app"
DMG_PATH="dist/OnTheSpot.dmg"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found at $APP_PATH"
  echo "Run ./scripts/build_macos_app.sh first"
  exit 1
fi

rm -f "$DMG_PATH"
hdiutil create -volname "On The Spot" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

echo "DMG created: $DMG_PATH"
