# app/main.py
from contextlib import asynccontextmanager

from cache import get_cache, set_cache
from discovery import LanAnnouncer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from settings import CORS_ORIGINS, logger

announcer = LanAnnouncer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Announce on the LAN (no-op unless YT2RSS_MDNS_ENABLED is set).
    await announcer.start()
    try:
        yield
    finally:
        await announcer.stop()


app = FastAPI(title="yt2rss - YouTube to Podcast RSS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Startup sanity check for the configured cache backend.
set_cache("_selftest", {"status": "up"})
logger.debug(f"cache status: {get_cache('_selftest')}")

# -------- Routes --------
# Imported after the app is created; the routers attach to it below.
import api  # noqa: E402

app.include_router(api.base.router)
app.include_router(api.extra.router)
app.include_router(api.core.router)
