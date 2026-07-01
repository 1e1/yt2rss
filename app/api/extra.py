# app/extra.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from settings import BASE_DIR

router = APIRouter(prefix="/extra", tags=["extra"])

EXT_DIR = BASE_DIR / "extra" / "extensions" / "subcRiSS"
BROWSERS = {"firefox", "chrome", "edge"}


@router.get("/extensions/subcRiSS/{browser}.zip")
async def extension(browser: str):
    if browser not in BROWSERS:
        raise HTTPException(status_code=404, detail="Unknown browser package")
    file_path = EXT_DIR / f"{browser}.zip"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{browser} extension zip not found")
    return FileResponse(
        path=file_path, filename=f"subcRiSS-{browser}.zip", media_type="application/zip"
    )
