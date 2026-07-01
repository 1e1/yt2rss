import os
import sys
import tempfile
from pathlib import Path

import pytest

# The app reads its configuration from the environment at import time, so the
# test environment must be set up *before* `main` is imported anywhere.
_TMP = tempfile.mkdtemp(prefix="yt2rss-tests-")
os.environ.setdefault("YT2RSS_CACHE_DIR", os.path.join(_TMP, "cache"))
os.environ.setdefault("YT2RSS_TMP_DIR", os.path.join(_TMP, "tmp"))
os.environ.setdefault("YT2RSS_CACHE_MODE", "disk")
os.environ.setdefault("YT2RSS_LOG_LEVEL", "ERROR")

# Make the application package importable (main, api, settings, cache).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))


@pytest.fixture
def sample_channel_info():
    """A representative yt-dlp channel extraction result."""
    return {
        "title": "Cool & <Channel>",
        "description": 'desc "quoted"',
        "webpage_url": "https://www.youtube.com/@handle",
        "thumbnails": [
            {"id": "avatar_uncropped", "url": "http://x/a.jpg?w=1&h=2"},
            {"id": "banner", "url": "http://x/b.jpg"},
        ],
        "entries": [
            {
                "id": "abc123DEF45",
                "title": "Ep 1 <b>",
                "url": "https://youtu.be/abc123DEF45",
                "description": "d1",
            },
        ],
    }


@pytest.fixture
def client(monkeypatch, sample_channel_info):
    """TestClient with yt-dlp stubbed out (no network) and cache disabled."""
    import cache
    import main
    from api import core
    from fastapi.testclient import TestClient

    monkeypatch.setattr(cache, "CACHE_MODE", "none")
    monkeypatch.setattr(core, "yt_extract_info_url", lambda url, opts=None: sample_channel_info)
    return TestClient(main.app)
