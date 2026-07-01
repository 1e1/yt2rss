#!/usr/bin/env bash
set -euo pipefail

# Build the subcRiSS browser extensions from a single MV2 source manifest.
#
#   ./build.sh [SRC_DIR] [OUT_DIR]
#
# Produces:
#   firefox.zip  -> Manifest V2 (event-page background, browser_action)
#   chrome.zip   -> Manifest V3 (service-worker background, action, scripting)
#
# Requires: jq, zip.

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${1:-$ROOT}"
OUT_DIR="${2:-$ROOT/dist}"

mkdir -p "$OUT_DIR"

if [ ! -f "$SRC_DIR/manifest.json" ]; then
  echo "manifest.json not found in $SRC_DIR" >&2
  exit 1
fi

build_target() {
  local name="$1" jq_filter="$2"
  local work
  work="$(mktemp -d)"
  cp -r "$SRC_DIR/." "$work/"
  rm -rf "$work/dist"
  jq "$jq_filter" "$SRC_DIR/manifest.json" > "$work/manifest.json"
  (
    cd "$work"
    rm -f "$OUT_DIR/$name.zip"
    zip -qr "$OUT_DIR/$name.zip" . \
      -x "*.DS_Store" -x "*/.git/*" -x "build.sh" -x "readme.md" -x "dist/*"
  )
  rm -rf "$work"
  echo "  - $name: $OUT_DIR/$name.zip"
}

echo "Building subcRiSS extensions…"

# Firefox: keep the source manifest as-is (Manifest V2).
build_target firefox '.'

# Chrome: derive a Manifest V3 variant.
build_target chrome '
  .manifest_version = 3
  | .action = .browser_action
  | del(.browser_action)
  | .background = {"service_worker": "background.js"}
  | .permissions += ["scripting"]
  | .host_permissions = ["*://*.youtube.com/*"]
  | del(.browser_specific_settings)
'

# Edge (and other Chromium browsers) use the same Manifest V3 package.
cp "$OUT_DIR/chrome.zip" "$OUT_DIR/edge.zip"
echo "  - edge: $OUT_DIR/edge.zip"

echo "Done."
