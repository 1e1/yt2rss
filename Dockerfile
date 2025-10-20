# Dockerfile — builds the app and packages the extensions into /app/extra/extensions/subcRiSS/
FROM python:3-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
#ENV PYTHONPATH=/app
WORKDIR /build

# Install system deps needed for runtime (ffmpeg) and packaging (zip, sed)
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

# Copy source files into build stage
# (expects directories: app/, subcRiSS/, requirements.txt, Dockerfile at repo root)
COPY . /build

# Create a script to build firefox.zip and chrome.zip
RUN mkdir -p /build/extra/extensions/subcRiSS && \
    cat > /build/build_extensions.sh <<'SH' && chmod +x /build/build_extensions.sh
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

SRC="${ROOT}/subcRiSS"
OUTDIR="${ROOT}/extra/extensions/subcRiSS"
mkdir -p "${OUTDIR}"

echo "Packing firefox extension..."
# zip the directory for firefox as-is (manifest uses browser.*)
(
  cd "${SRC}"
  zip -r "${OUTDIR}/firefox.zip" . -x "*.DS_Store" -x "*/.git/*"
)

echo "Packing chrome extension (compat shim)..."
# create a temp work dir to modify JS files for Chrome compatibility
TMP="$(mktemp -d)"
cp -r "${SRC}/." "${TMP}/"
# For each .js file, prepend a small shim that maps browser -> chrome if needed
SHIM='if (typeof browser === "undefined" && typeof chrome !== "undefined") { var browser = chrome; }'

# Prepend shim to service worker/background and content scripts
find "${TMP}" -type f -name "*.js" | while read -r js; do
  # Prepend only if not already having the shim
  if ! grep -q "var browser = chrome" "$js"; then
    printf "%s\n\n" "$SHIM" | cat - "$js" > "$js.tmp" && mv "$js.tmp" "$js"
  fi
done

(
  cd "${TMP}"
  zip -r "${OUTDIR}/chrome.zip" . -x "*.DS_Store" -x "*/.git/*"
)

# cleanup
rm -rf "${TMP}"
echo "Extensions created:"
ls -l "${OUTDIR}"

SH
# Run the extension build script during image build
RUN /build/build_extensions.sh

# ---------- Final image ----------
FROM python:3-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
WORKDIR /app

# Install runtime deps (ffmpeg etc)
RUN apk add --no-cache ffmpeg curl ca-certificates

# Copy requirements + app code
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY app /app

# Copy generated extension zips from build stage
COPY --from=build /build/extra /app/extra

# create data directories (mounted or internal)
RUN mkdir -p /data/cache /data/tmp

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
