# app/settings.py
# Shared configuration and logging. This module must not import `api` or `main`
# so the import graph stays acyclic (settings <- cache <- api <- main).
import logging
import os
from pathlib import Path

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = os.environ.get("YT2RSS_CACHE_DIR", "/data/cache")
TMP_DIR = os.environ.get("YT2RSS_TMP_DIR", "/data/tmp")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# ---------- Cache ----------
CACHE_MODE = os.getenv("YT2RSS_CACHE_MODE", "disk").lower()  # disk | memcache | none
# Default TTL, used when a caller does not pass an explicit one.
CHANNEL_CACHE_TTL = int(
    os.environ.get("YT2RSS_CHANNEL_TTL", os.environ.get("YT2RSS_CACHE_TTL", "600"))
)
MEMCACHE_HOST = os.getenv("YT2RSS_MEMCACHE_HOST", "memcached")
MEMCACHE_PORT = int(os.getenv("YT2RSS_MEMCACHE_PORT", "11211"))

# ---------- HTTP ----------
# Comma-separated list of allowed origins, or "*" (default) to allow any.
CORS_ORIGINS = [o.strip() for o in os.getenv("YT2RSS_CORS_ORIGINS", "*").split(",") if o.strip()]

# ---------- LAN discovery (mDNS / DNS-SD) ----------
# Opt-in: advertise this instance on the local network so other services can
# discover it. In Docker this requires host networking to reach the LAN.
MDNS_ENABLED = os.getenv("YT2RSS_MDNS_ENABLED", "false").lower() in ("1", "true", "yes", "on")
MDNS_NAME = os.getenv("YT2RSS_MDNS_NAME", "yt2rss")
MDNS_TYPE = os.getenv("YT2RSS_MDNS_TYPE", "_http._tcp.local.")
MDNS_PORT = int(os.getenv("YT2RSS_MDNS_PORT", "8000"))

# ---------- Logging ----------
LOG_LEVEL = os.environ.get("YT2RSS_LOG_LEVEL", "ERROR").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("yt2rss")

logger.info(f"[yt2rss] env YT2RSS_CACHE_MODE={CACHE_MODE}")
