# app/core.py
import os
import asyncio
import tempfile
import httpx
import re
from datetime import datetime
import email.utils
from fastapi import APIRouter, Request, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from main import (
    get_cache, set_cache,
    logger,
    TMP_DIR
)
from yt_dlp import YoutubeDL

# -------- Configuration ----------
RSS_MAX_ITEMS = int(os.environ.get("YT2RSS_MAX_ITEMS", "10"))
DEFAULT_VIDEO_HEIGHT = int(os.environ.get("YT2RSS_MAX_HEIGHT", "720"))

YDL_OPTS = {"quiet": True, "skip_download": True, "no_warnings": True}

def xml_escape(text: Optional[str]) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

def sanitize_filename(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name[:200]

def get_base_url(request: Request) -> str:
    return request.url.scheme + "://" + request.url.netloc

def choose_combined_mp4(formats: List[Dict], max_height: int = DEFAULT_VIDEO_HEIGHT) -> Optional[Dict]:
    if not formats:
        return None
    candidates = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none"]
    if not candidates:
        return None
    def score(f):
        ext = (f.get("ext") or "").lower()
        pref_ext = 0 if ext == "mp4" else 1
        height = f.get("height") or 0
        penalty = abs(height - max_height) + (5000 if height > max_height else 0)
        return (pref_ext, penalty, -height)
    return sorted(candidates, key=score)[0]

def yt_extract_info_video(video_id: str, opts_extra: dict = None) -> Dict:
    vcache_key = f"v_{video_id}"
    vinfo = get_cache(vcache_key)
    if not vinfo:
        url = f"https://www.youtube.com/watch?v={video_id}"
        vinfo = yt_extract_info_url(url, opts_extra)
        set_cache(vcache_key, vinfo)
    return vinfo
    
def yt_extract_info_url(url: str, opts_extra: dict = None) -> Dict:
    opts = dict(YDL_OPTS)
    if opts_extra:
        opts.update(opts_extra)
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

router = APIRouter(tags=["core"])

@router.get("/playlist.rss")
async def playlist_rss(request: Request, list: str = Query(...), max_items: int = Query(RSS_MAX_ITEMS)):
    base_url = get_base_url(request)
    playlist_url = f"https://www.youtube.com/playlist?list={list}"
    return await _generate_rss_for_collection(base_url, playlist_url, max_items)

@router.get("/{path:path}.rss")
async def dynamic_rss(request: Request, path: str, max_items: int = Query(RSS_MAX_ITEMS)):
    base_url = get_base_url(request)
    def ensure_videos_suffix(url: str) -> str:
        return url if url.endswith("/videos") else f"{url}/videos"

    if path.startswith("_user/"):
        handle = path[len("_user/"):]
        target = ensure_videos_suffix(f"https://www.youtube.com/@{handle}")
    elif path.startswith("@"):
        target = ensure_videos_suffix(f"https://www.youtube.com/{path}")
    elif path.startswith(("c/", "channel/", "user/")):
        target = ensure_videos_suffix(f"https://www.youtube.com/{path}")
    else:
        target = ensure_videos_suffix(f"https://www.youtube.com/c/{path}")

    return await _generate_rss_for_collection(base_url, target, max_items)

async def _generate_rss_for_collection(base_url: str, target_url: str, max_items: int):
    url_path = '/'.join(target_url.split('/')[3:])
    if url_path.startswith('@'):
        url_path = '_user/' + url_path[1:]
    cache_key = f"rss::{url_path}::i{max_items}"
    cached = get_cache(cache_key)
    if cached:
        xml = cached["xml"].encode("utf-8")
        return Response(content=xml, media_type="text/xml")

    opts_extra = {
        "extract_flat": True,
        "playlistend": max_items,
        "force_generic_extractor": False,
    }
    try:
        info = yt_extract_info_url(target_url, opts_extra)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction échouée: {e}")

    feed_title = xml_escape(info.get("title") or target_url)
    feed_desc = xml_escape(info.get("description") or f"Flux depuis {feed_title}")
    feed_link = info.get("webpage_url") or target_url
    avatar_url = [thumb["url"] for thumb in info.get("thumbnails") if thumb.get("id") == "avatar_uncropped"]
    feed_thumb = avatar_url[0] if avatar_url else None

    entries = [e for e in (info.get("entries") or [info]) if e][:max_items]

    # --- Warmup async 1st video ---
    if entries:
        first = entries[0]
        vid = first.get("id") or (first.get("url") or "").split("v=")[-1]
        async def warmup_video(video_id: str):
            try:
                logger.info(f"[warmup] Pre-fetching video metadata for {video_id} ...")
                yt_extract_info_video(video_id)
                logger.debug(f"[warmup] Cached video {video_id}")
            except Exception as e:
                logger.warning(f"[warmup] Skipped {video_id}: {e}")

        # task in background
        asyncio.create_task(warmup_video(vid))

    # --- generate RSS ---
    items = ""
    for e in entries:
        vid = e.get("id") or (e.get("url") or "").split("v=")[-1]
        title = xml_escape(e.get("title") or "Video")
        desc = xml_escape(e.get("description"))
        redirect_url = f"{base_url}/redirect/{vid}.mp4" if base_url else f"/video/{redirect}.mp4"
        dl_url = f"{base_url}/video/{vid}.mp4" if base_url else f"/video/{vid}.mp4"
        items += f"""
        <item>
          <title>{title}</title>
          <link>{e.get("url")}</link>
          <guid>y2rss::{vid}</guid>
          <description><![CDATA[{desc} [proxy: {dl_url}]]]></description>
          <enclosure url="{redirect_url}" type="video/mp4" />
        </item>
        """

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{feed_title}</title>
  <link>{feed_link}</link>
  <description>{feed_desc}</description>
  <image>{feed_thumb}</image>
  {items}
</channel>
</rss>"""

    set_cache(cache_key, {"xml": rss})
    return Response(content=rss.encode("utf-8"), media_type="text/xml")

@router.get("/redirect/{video_id}.mp4")
async def redirect_video_endpoint(video_id: str, height: int = Query(DEFAULT_VIDEO_HEIGHT)):
    """
    Renvoie une redirection HTTP vers la source MP4 originale sur YouTube.
    Utilise le même mécanisme de sélection que /video/{video_id}.mp4.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        info = yt_extract_info_video(video_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible d'extraire la vidéo: {e}")

    chosen = choose_combined_mp4(info.get("formats") or [], height)
    if not chosen or not chosen.get("url"):
        raise HTTPException(status_code=404, detail="Aucune source MP4 trouvée")

    title = sanitize_filename(info.get("title") or "video")
    filename = f"{title}.mp4"

    response = Response(
        status_code=302,
        headers={
            "Location": chosen["url"],
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
    return response

@router.get("/video/{video_id}.mp4")
async def video_endpoint(video_id: str, height: int = Query(DEFAULT_VIDEO_HEIGHT)):
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        info = yt_extract_info_video(video_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible d'extraire la vidéo: {e}")

    title = sanitize_filename(info.get("title") or "video")
    filename = f"{title}.mp4"

    chosen = choose_combined_mp4(info.get("formats") or [], height)
    if chosen and chosen.get("url") and (chosen.get("ext") == "mp4"):
        client = httpx.AsyncClient(timeout=None)

        async def stream():
            async with client.stream("GET", chosen["url"], follow_redirects=True) as r:
                async for chunk in r.aiter_bytes(256 * 1024):
                    yield chunk
            await client.aclose()

        return StreamingResponse(
            stream(),
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    logger.info(f"[download] fallback tmp")
    # fallback: téléchargement temporaire
    tmpfd, tmp_path = tempfile.mkstemp(prefix="yt2rss_", suffix=".mp4", dir=TMP_DIR)
    os.close(tmpfd)
    ydl_opts = {
        "outtmpl": tmp_path,
        "format": f"bestvideo[height<={height}]+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=f"Erreur téléchargement: {e}")

    def file_iter(path):
        with open(path, "rb") as f:
            yield from iter(lambda: f.read(256 * 1024), b"")
        os.remove(path)

    return StreamingResponse(
        file_iter(tmp_path),
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

