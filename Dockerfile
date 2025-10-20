# ===========================================================
#  STAGE 1 — BUILD EXTENSIONS + PYTHON BYTECODE
# ===========================================================
FROM python:3-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /build

# --- Install system dependencies ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      curl \
      ca-certificates \
      zip \
      unzip \
      sed \
      git && \
    rm -rf /var/lib/apt/lists/*

# --- Copy source files ---
COPY . /build

# --- Build browser extensions (firefox + chrome) ---
RUN mkdir -p /build/extra/extensions/subcRiSS && \
    cat > /build/build_extensions.sh <<'SH' && chmod +x /build/build_extensions.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

SRC="${ROOT}/subcRiSS"
OUTDIR="${ROOT}/extra/extensions/subcRiSS"
mkdir -p "${OUTDIR}"

echo "📦 Packing Firefox extension..."
(
  cd "${SRC}"
  zip -r "${OUTDIR}/firefox.zip" . -x "*.DS_Store" -x "*/.git/*"
)

echo "📦 Packing Chrome extension..."
TMP="$(mktemp -d)"
cp -r "${SRC}/." "${TMP}/"
SHIM='if (typeof browser === "undefined" && typeof chrome !== "undefined") { var browser = chrome; }'
find "${TMP}" -type f -name "*.js" | while read -r js; do
  if ! grep -q "var browser = chrome" "$js"; then
    printf "%s\n\n" "$SHIM" | cat - "$js" > "$js.tmp" && mv "$js.tmp" "$js"
  fi
done
(
  cd "${TMP}"
  zip -r "${OUTDIR}/chrome.zip" . -x "*.DS_Store" -x "*/.git/*"
)
rm -rf "${TMP}"
echo "✅ Extensions created:"
ls -lh "${OUTDIR}"
SH
RUN /build/build_extensions.sh

# ===========================================================
#  STAGE 2 — FINAL IMAGE WITH OPTIMIZATIONS
# ===========================================================
FROM python:3-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
WORKDIR /app

# --- Install runtime dependencies ---
RUN apk add --no-cache ffmpeg curl ca-certificates

# --- Copy code and dependencies ---
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app
COPY --from=build /build/extra /app/extra

# --- Prepare cache folders ---
RUN mkdir -p /data/cache /data/tmp

# ===========================================================
#  PERFORMANCE BOOSTS
# ===========================================================

# 🧩 Precompile all Python code to .pyc (faster startup)
RUN python -m compileall -q /app

# 🔥 Pre-warm yt-dlp to build extractor cache
RUN python - <<'PY'
from yt_dlp import YoutubeDL
print("🔥 Warming up yt-dlp extractors (first call might take a few seconds)...")
ydl = YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True})
try:
    ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
    print("✅ yt-dlp warmup complete.")
except Exception as e:
    print("⚠️ Warmup failed:", e)
PY

# ===========================================================
#  SERVER LAUNCH (single persistent worker)
# ===========================================================
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--http", "httptools", "--workers", "1", "--limit-concurrency", "5"]
