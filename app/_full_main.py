# app/main.py
import os
import json
import time
import tempfile
import re
import asyncio
from typing import Optional, List, Dict
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor

import logging
import httpx
from fastapi import FastAPI, Request, Query, HTTPException, Response, Path
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from yt_dlp import YoutubeDL

# -------- Configuration (env) ----------
CACHE_DIR = os.environ.get("YT2RSS_CACHE_DIR", "/data/cache")
TMP_DIR = os.environ.get("YT2RSS_TMP_DIR", "/data/tmp")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# TTL for channel/rss cache (seconds)
CHANNEL_CACHE_TTL = int(os.environ.get("YT2RSS_CHANNEL_TTL", os.environ.get("YT2RSS_CACHE_TTL", "600")))
# max items in RSS
RSS_MAX_ITEMS = int(os.environ.get("YT2RSS_MAX_ITEMS", "20"))
# default requested max height for video
DEFAULT_VIDEO_HEIGHT = int(os.environ.get("YT2RSS_MAX_HEIGHT", "720"))
# base url for absolute enclosure links (optional)
BASE_URL = os.environ.get("YT2RSS_BASE_URL", "").rstrip("/")

# parallel workers for metadata extraction
MAX_WORKERS = min(4, (os.cpu_count() or 2))
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# yt-dlp base options
YDL_OPTS = {
    "quiet": True,
    "skip_download": True,
    "no_warnings": True,
}

# logging
LOG_LEVEL = os.environ.get("YT2RSS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("yt2rss")

app = FastAPI(title="yt2rss - YouTube to Podcast RSS")

# CORS (optionnel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Paths ----------
BASE_DIR = Path(__file__).parent
EXT_DIR = BASE_DIR.parent / "extra" / "extensions" / "subcRiSS"  # /app/extra/extensions/subcRiSS
HOMEPAGE = BASE_DIR / "index.html"

# -------- Helpers: cache ----------
def cache_path_for_key(key: str) -> str:
    safe = quote_plus(key)
    return os.path.join(CACHE_DIR, f"{safe}.json")

def get_cache(key: str) -> Optional[Dict]:
    p = cache_path_for_key(key)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
        ts = obj.get("_cached_at", 0)
        if time.time() - ts > CHANNEL_CACHE_TTL:
            logger.debug("Cache expired for key %s", key)
            return None
        return obj.get("value")
    except Exception as e:
        logger.warning("Failed reading cache %s: %s", p, e)
        return None

def set_cache(key: str, value: Dict):
    p = cache_path_for_key(key)
    tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"_cached_at": int(time.time()), "value": value}, f)
        os.replace(tmp, p)
    except Exception as e:
        logger.warning("Failed writing cache %s: %s", p, e)

# -------- Helpers: xml sanitize & filename ----------
def xml_escape(text: Optional[str]) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name[:200]

# -------- Helpers: format selection & yt-dlp extraction ----------
def choose_combined_mp4(formats: List[Dict], max_height: int = DEFAULT_VIDEO_HEIGHT) -> Optional[Dict]:
    if not formats:
        return None
    candidates = []
    for f in formats:
        prot = (f.get("protocol") or "").lower()
        if "m3u8" in prot or "dash" in prot:
            continue
        if f.get("vcodec") != "none" and f.get("acodec") != "none":
            candidates.append(f)
    if not candidates:
        return None
    def score(f):
        ext = (f.get("ext") or "").lower()
        pref_ext = 0 if ext == "mp4" else 1
        height = f.get("height") or 0
        height_penalty = abs(height - max_height)
        if height > max_height:
            height_penalty += 5000
        return (pref_ext, height_penalty, -height)
    return sorted(candidates, key=score)[0]

def yt_extract_info(url: str, opts_extra: dict = None) -> Dict:
    opts = dict(YDL_OPTS)
    if opts_extra:
        opts.update(opts_extra)
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

# -------- Async metadata fetch (threadpool based) ----------
async def fetch_video_metadata(video_url: str) -> dict:
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(executor, lambda: yt_extract_info(video_url))
        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "url": info.get("webpage_url"),
            "description": info.get("description"),
            "thumbnail": info.get("thumbnail"),
            "upload_date": info.get("upload_date"),
            "duration": info.get("duration"),
        }
    except Exception as e:
        logger.debug("Metadata fetch failed for %s: %s", video_url, e)
        return {"url": video_url}

# -------- Endpoints ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if HOMEPAGE.exists():
        return HTMLResponse(content=HOMEPAGE.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>yt2rss — Homepage not found</h1>", status_code=404)

@app.get("/extra/extensions/subcRiSS/firefox.zip")
async def firefox_extension():
    file_path = EXT_DIR / "firefox.zip"
    if not file_path.exists():
        return {"error": "Firefox extension zip not found."}
    return FileResponse(path=file_path, filename="subcRiSS-firefox.zip", media_type="application/zip")


@app.get("/extra/extensions/subcRiSS/chrome.zip")
async def chrome_extension():
    file_path = EXT_DIR / "chrome.zip"
    if not file_path.exists():
        return {"error": "Chrome extension zip not found."}
    return FileResponse(path=file_path, filename="subcRiSS-chrome.zip", media_type="application/zip")

@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"

@app.get("/playlist.rss")
async def playlist_rss(list: str = Query(..., description="playlist id"),
                       max_items: int = Query(RSS_MAX_ITEMS)):
    playlist_url = f"https://www.youtube.com/playlist?list={list}"
    return await _generate_rss_for_collection(playlist_url, max_items=max_items)

# dynamic route that accepts slashes in path (so _user/handle works)
@app.get("/{path:path}.rss")
async def dynamic_rss(path: str, max_items: int = Query(RSS_MAX_ITEMS)):
    if path.startswith("_user/"):
        handle = path[len("_user/"):]
        target = f"https://www.youtube.com/@{handle}"
    elif path.startswith("@"):
        target = f"https://www.youtube.com/{path}"
    elif path.startswith("c/") or path.startswith("channel/") or path.startswith("user/"):
        target = f"https://www.youtube.com/{path}"
    else:
        target = f"https://www.youtube.com/c/{path}"
    return await _generate_rss_for_collection(target, max_items=max_items)

async def _generate_rss_for_collection(target_url: str, max_items: int = RSS_MAX_ITEMS):
    cache_key = f"rss::{target_url}::items={max_items}"
    cached = get_cache(cache_key)
    if cached:
        rss_bytes = cached["xml"].encode("utf-8")
        return Response(content=rss_bytes, media_type="text/xml", headers={
            "Content-Length": str(len(rss_bytes)),
            "Content-Type": "text/xml; charset=UTF-8"
        })

    opts_extra = {"extract_flat": True, "playlistend": max_items}
    try:
        info = yt_extract_info(target_url, opts_extra=opts_extra)
    except Exception as e:
        logger.warning("Failed extracting collection %s : %s", target_url, e)
        raise HTTPException(status_code=400, detail=f"Impossible d'extraire la source: {e}")

    entries = info.get("entries") or [info]
    entries = [e for e in entries if e is not None][:max_items]

    # build list of video URLs to enrich in parallel
    video_urls = [e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}" for e in entries]
    # parallel metadata fetch (uses threadpool)
    try:
        metadatas = await asyncio.gather(*(fetch_video_metadata(url) for url in video_urls))
    except Exception as e:
        logger.debug("Parallel metadata gather error: %s", e)
        metadatas = [{"url": url} for url in video_urls]

    feed_title = xml_escape(info.get("title") or target_url)
    feed_link = info.get("webpage_url") or target_url
    feed_desc = xml_escape(info.get("description") or f"Flux podcast auto-généré depuis {feed_title}")

    items_xml = ""
    for e in metadatas:
        video_id = e.get("id") or (e.get("url") or "").split("v=")[-1]
        title = xml_escape(e.get("title") or "Video")
        webpage_url = e.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        description = xml_escape(e.get("description"))
        thumbnail = e.get("thumbnail") or ""

        enc_url = f"{BASE_URL}/dl?v={video_id}" if BASE_URL else f"/dl?v={video_id}"

        items_xml += f"""
        <item>
          <title>{title}</title>
          <link>{webpage_url}</link>
          <guid isPermaLink="false">{video_id}</guid>
          <description><![CDATA[{description}]]></description>
          {f"<thumbnail>{thumbnail}</thumbnail>" if thumbnail else ""}
          <enclosure url="{enc_url}" type="video/mp4" />
        </item>
        """

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{feed_title}</title>
  <link>{feed_link}</link>
  <description>{feed_desc}</description>
  {items_xml}
</channel>
</rss>
"""
    set_cache(cache_key, {"xml": rss})
    rss_bytes = rss.encode("utf-8")
    return Response(content=rss_bytes, media_type="text/xml", headers={
        "Content-Length": str(len(rss_bytes)),
        "Content-Type": "text/xml; charset=UTF-8"
    })

# /dl endpoint : stream MP4 when possible, else download+merge to tmp and stream
@app.get("/dl")
async def dl_endpoint(v: Optional[str] = Query(None),
                      video_url: Optional[str] = Query(None),
                      height: Optional[int] = Query(DEFAULT_VIDEO_HEIGHT)):
    if not v and not video_url:
        raise HTTPException(status_code=400, detail="v (video id) or video_url required")
    if v:
        video_url = f"https://www.youtube.com/watch?v={v}"

    try:
        info = yt_extract_info(video_url)
    except Exception as e:
        logger.warning("Failed extract for dl %s: %s", video_url, e)
        raise HTTPException(status_code=400, detail=f"Impossible d'extraire la vidéo: {e}")

    title = info.get("title") or "video"
    sanitized_title = sanitize_filename(title)
    filename = f"{sanitized_title}.mp4"

    formats = info.get("formats") or []
    chosen = choose_combined_mp4(formats, max_height=height)

    # if direct mp4 combined format exists, proxy/stream it
    if chosen and chosen.get("url") and (chosen.get("ext") or "").lower() == "mp4":
        target_url = chosen["url"]
        client = httpx.AsyncClient(timeout=None)
        async def stream_by_chunks():
            try:
                async with client.stream("GET", target_url, follow_redirects=True, timeout=None) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes(chunk_size=256*1024):
                        yield chunk
            finally:
                await client.aclose()
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(chosen.get("filesize", 0))
        }
        return StreamingResponse(stream_by_chunks(), media_type="video/mp4", headers=headers)

    # fallback: download+merge into temp file (mp4) then stream and delete
    tmpfd, tmp_path = tempfile.mkstemp(prefix="yt2rss_", suffix=".mp4", dir=TMP_DIR)
    os.close(tmpfd)

    ydl_opts = {
        "outtmpl": tmp_path,
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        logger.warning("yt-dlp download failed for %s: %s", video_url, e)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Erreur téléchargement temporaire: {e}")

    def file_iterator(path, chunk_size=256*1024):
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(os.path.getsize(tmp_path))
    }
    return StreamingResponse(file_iterator(tmp_path), media_type="video/mp4", headers=headers)
