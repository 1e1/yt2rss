# app/main.py
import asyncio
import memcache
import os
import json
import time
from typing import Optional, Dict
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -------- Configuration ----------
CACHE_DIR = os.environ.get("YT2RSS_CACHE_DIR", "/data/cache")
TMP_DIR = os.environ.get("YT2RSS_TMP_DIR", "/data/tmp")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

CHANNEL_CACHE_TTL = int(os.environ.get("YT2RSS_CHANNEL_TTL", os.environ.get("YT2RSS_CACHE_TTL", "600")))

MAX_WORKERS = min(4, (os.cpu_count() or 2))
#executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

LOG_LEVEL = os.environ.get("YT2RSS_LOG_LEVEL", "ERROR").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("yt2rss")

# --- Cache configuration ---
CACHE_MODE = os.getenv("YT2RSS_CACHE_MODE", "disk").lower()  # disk | memcache | none

logger.info(f"[yt2rss] env YT2RSS_CACHE_MODE={CACHE_MODE}")

memcache_client = None
if CACHE_MODE == "memcache":
    MEMCACHE_HOST = os.getenv("YT2RSS_MEMCACHE_HOST", "memcached")
    MEMCACHE_PORT = int(os.getenv("YT2RSS_MEMCACHE_PORT", "11211"))
    try:
        memcache_client = memcache.Client([(f"{MEMCACHE_HOST}:{MEMCACHE_PORT}")], debug=0)
    except Exception as e:
        logger.warning(f"[yt2rss] ⚠️ Could not connect to memcache: {e}")
        memcache_client = None
    logger.info(f"[yt2rss] Using memcache at {MEMCACHE_HOST}:{MEMCACHE_PORT}")
elif CACHE_MODE == "disk":
        logger.info(f"[yt2rss] Using disk cache at {CACHE_DIR}")


app = FastAPI(title="yt2rss - YouTube to Podcast RSS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent

# -------- Helpers ----------
def cache_path_for_key(key: str) -> str:
    safe = quote_plus(key)
    return os.path.join(CACHE_DIR, f"{safe}.json")


def get_cache(key: str) -> Optional[Dict]:
    logger.debug(f"[cache] raw check {key}")
    if CACHE_MODE == "none":
        return None

    if CACHE_MODE == "memcache" and memcache_client:
        try:
            val = memcache_client.get(key)
            if val:
                data = json.loads(val)
                logger.debug(f"[cache] get({key}) => {val!r}")
                return data.get("value")
            return None
        except Exception as e:
            logger.error(f"[yt2rss] memcache get error: {e}")
            return None

    # fallback: disk cache
    path_key = cache_path_for_key(key)
    logger.debug(f"[cache] disk check {path_key}")
    if not os.path.isfile(p):
        return None
    try:
        with open(path_key, "r", encoding="utf-8") as f:
            obj = json.load(f)
        ts = obj.get("_cached_at", 0)
        if time.time() - ts > CHANNEL_CACHE_TTL:
            os.remove(path_key)
            return None
        logger.debug(f"[cache] get({mem_key}) => {val!r}")
        return obj.get("value")
    except Exception:
        return None


def set_cache(key: str, value: Dict) -> None:
    logger.debug(f"[cache] raw set {key}")
    if CACHE_MODE == "none":
        return

    payload = {"_cached_at": time.time(), "value": value}
    if CACHE_MODE == "memcache" and memcache_client:
        try:
            memcache_client.set(key, json.dumps(payload), time=CHANNEL_CACHE_TTL)
            return
        except Exception as e:
            logger.error(f"[yt2rss] memcache set error: {e}")

    # fallback disk cache
    path_key = cache_path_for_key(key)
    logger.debug(f"[cache] disk set {path_key}")
    try:
        with open(path_key, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception as e:
        logger.error(f"[yt2rss] disk cache set error: {e}")


set_cache("test", "UP")
v = get_cache("test")
logger.debug(f"cache status: {v}")

# -------- Import des routes --------
import api

app.include_router(api.base.router)
#app.include_router(api.extra.router)
app.include_router(api.core.router)
