# app/cache.py
# Cache backend (disk | memcache | none). Depends only on `settings`.
import json
import os
import time
from urllib.parse import quote_plus

import memcache
from settings import (
    CACHE_DIR,
    CACHE_MODE,
    CHANNEL_CACHE_TTL,
    MEMCACHE_HOST,
    MEMCACHE_PORT,
    logger,
)

memcache_client = None
if CACHE_MODE == "memcache":
    try:
        memcache_client = memcache.Client([f"{MEMCACHE_HOST}:{MEMCACHE_PORT}"], debug=0)
        logger.info(f"[yt2rss] Using memcache at {MEMCACHE_HOST}:{MEMCACHE_PORT}")
    except Exception as e:
        logger.warning(f"[yt2rss] ⚠️ Could not connect to memcache: {e}")
        memcache_client = None
elif CACHE_MODE == "disk":
    logger.info(f"[yt2rss] Using disk cache at {CACHE_DIR}")


def cache_path_for_key(key: str) -> str:
    safe = quote_plus(key)
    return os.path.join(CACHE_DIR, f"{safe}.json")


def get_cache(key: str) -> dict | None:
    logger.debug(f"[cache] raw check {key}")
    if CACHE_MODE == "none":
        return None

    if CACHE_MODE == "memcache" and memcache_client:
        try:
            val = memcache_client.get(key)
            if val:
                logger.debug(f"[cache] get({key}) => hit")
                return json.loads(val).get("value")
            return None
        except Exception as e:
            logger.error(f"[yt2rss] memcache get error: {e}")
            return None

    # fallback: disk cache
    path_key = cache_path_for_key(key)
    logger.debug(f"[cache] disk check {path_key}")
    if not os.path.isfile(path_key):
        return None
    try:
        with open(path_key, encoding="utf-8") as f:
            obj = json.load(f)
        ts = obj.get("_cached_at", 0)
        ttl = obj.get("_ttl", CHANNEL_CACHE_TTL)
        if time.time() - ts > ttl:
            os.remove(path_key)
            return None
        logger.debug(f"[cache] get({key}) => hit")
        return obj.get("value")
    except Exception:
        return None


def set_cache(key: str, value: dict, ttl: int | None = None) -> None:
    logger.debug(f"[cache] raw set {key}")
    if CACHE_MODE == "none":
        return

    ttl = CHANNEL_CACHE_TTL if ttl is None else ttl
    payload = {"_cached_at": time.time(), "_ttl": ttl, "value": value}
    if CACHE_MODE == "memcache" and memcache_client:
        try:
            memcache_client.set(key, json.dumps(payload), time=ttl)
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
