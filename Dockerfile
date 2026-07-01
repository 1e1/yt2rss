# ===========================================================
#  STAGE 1 — BUILD BROWSER EXTENSIONS
# ===========================================================
FROM alpine:3 AS build
WORKDIR /build

# jq + zip to assemble the Firefox (MV2) and Chrome (MV3) packages.
RUN apk add --no-cache bash jq zip

COPY subcRiSS /build/subcRiSS
RUN /build/subcRiSS/build.sh /build/subcRiSS /build/extra/extensions/subcRiSS

# ===========================================================
#  STAGE 2 — RUNTIME IMAGE
# ===========================================================
FROM python:3-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
WORKDIR /app

# --- Runtime dependencies (ffmpeg is required by yt-dlp for muxed fallback) ---
RUN apk add --no-cache ffmpeg ca-certificates

# --- Python dependencies ---
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Application code and pre-built extensions ---
COPY app /app
COPY --from=build /build/extra /app/extra

# --- Cache / temp folders ---
RUN mkdir -p /data/cache /data/tmp

# Precompile to .pyc for faster cold starts.
RUN python -m compileall -q /app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--loop", "uvloop", "--http", "httptools", "--workers", "1", \
     "--limit-concurrency", "5"]
