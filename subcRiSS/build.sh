#!/usr/bin/env bash
set -e

SRC_DIR="/build/subcRiSS"
OUT_DIR="/app/extra/extensions/subcRiSS"

mkdir -p "$OUT_DIR"

echo "🚀 Building subcRiSS extensions for Chrome and Firefox..."

# ---------- Common sanity check ----------
if [ ! -f "$SRC_DIR/manifest.json" ]; then
  echo "❌ manifest.json not found in $SRC_DIR"
  exit 1
fi

# ---------- Build Chrome ----------
echo "🔧 Building Chrome version..."
cp -r "$SRC_DIR" "$OUT_DIR/chrome"
jq '.background = { "service_worker": "background.js" } | .manifest_version = 3' \
  "$SRC_DIR/manifest.json" > "$OUT_DIR/chrome/manifest.json"
cd "$OUT_DIR/chrome" && zip -r ../chrome.zip . > /dev/null && cd - > /dev/null

# ---------- Build Firefox ----------
echo "🦊 Building Firefox version..."
cp -r "$SRC_DIR" "$OUT_DIR/firefox"
jq '.background = { "scripts": ["background.js"] } | .manifest_version = 2' \
  "$SRC_DIR/manifest.json" > "$OUT_DIR/firefox/manifest.json"
cd "$OUT_DIR/firefox" && zip -r ../firefox.zip . > /dev/null && cd - > /dev/null

echo "✅ Done."
echo "   - Firefox: $OUT_DIR/firefox.zip"
echo "   - Chrome:  $OUT_DIR/chrome.zip"
