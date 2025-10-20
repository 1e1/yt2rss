# app/extra.py
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from main import BASE_DIR

router = APIRouter(prefix="/extra", tags=["extra"])

EXT_DIR = BASE_DIR / "extra" / "extensions" / "subcRiSS"

@router.get("/extensions/subcRiSS/firefox.zip")
async def firefox_extension():
    file_path = EXT_DIR / "firefox.zip"
    if not file_path.exists():
        return {"error": "Firefox extension zip not found."}
    return FileResponse(path=file_path, filename="subcRiSS-firefox.zip", media_type="application/zip")

@router.get("/extensions/subcRiSS/chrome.zip")
async def chrome_extension():
    file_path = EXT_DIR / "chrome.zip"
    if not file_path.exists():
        return {"error": "Chrome extension zip not found."}
    return FileResponse(path=file_path, filename="subcRiSS-chrome.zip", media_type="application/zip")
