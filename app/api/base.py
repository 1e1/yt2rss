# app/base.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pathlib import Path
from main import BASE_DIR

router = APIRouter()

HOMEPAGE = BASE_DIR / "index.html"
HELPPAGE = BASE_DIR / "help.html"

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if HOMEPAGE.exists():
        return HTMLResponse(content=HOMEPAGE.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>yt2rss — Homepage not found</h1>", status_code=404)

@router.get("/help", response_class=HTMLResponse)
async def help(request: Request):
    if HELPPAGE.exists():
        return HTMLResponse(content=HELPPAGE.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>yt2rss — Help not found</h1>", status_code=404)

@router.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"
