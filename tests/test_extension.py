import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_index_has_handshake_marker():
    # The extension relies on this marker to auto-register the server on click.
    html = (REPO / "app" / "index.html").read_text(encoding="utf-8")
    assert 'name="yt2rss-server"' in html


def test_manifest_is_valid():
    manifest = json.loads((REPO / "subcRiSS" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 2
    matches = [m for cs in manifest["content_scripts"] for m in cs["matches"]]
    assert any("youtube.com" in m for m in matches)
    # Detection-on-click only needs activeTab, never broad host access.
    assert "activeTab" in manifest["permissions"]


def test_extension_unknown_browser_404(client):
    assert client.get("/extra/extensions/subcRiSS/opera.zip").status_code == 404


def test_extension_missing_file_404(client):
    # firefox is a known target but the built zip is absent from the source tree
    assert client.get("/extra/extensions/subcRiSS/firefox.zip").status_code == 404


@pytest.mark.parametrize("browser", ["firefox", "chrome", "edge"])
def test_extension_serves_built_zip(client, tmp_path, monkeypatch, browser):
    from api import extra

    (tmp_path / f"{browser}.zip").write_bytes(b"PK\x03\x04dummy")
    monkeypatch.setattr(extra, "EXT_DIR", tmp_path)
    r = client.get(f"/extra/extensions/subcRiSS/{browser}.zip")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert f"subcRiSS-{browser}.zip" in r.headers.get("content-disposition", "")


@pytest.mark.skipif(not (shutil.which("jq") and shutil.which("zip")), reason="jq and zip required")
def test_build_sh_produces_all_packages(tmp_path):
    src = REPO / "subcRiSS"
    out = tmp_path / "dist"
    subprocess.run(
        ["bash", str(src / "build.sh"), str(src), str(out)],
        check=True,
        capture_output=True,
    )
    for name in ("firefox.zip", "chrome.zip", "edge.zip"):
        assert (out / name).exists()
    # Edge ships the exact Chromium package.
    assert (out / "edge.zip").read_bytes() == (out / "chrome.zip").read_bytes()
    with zipfile.ZipFile(out / "chrome.zip") as z:
        manifest = json.loads(z.read("manifest.json"))
    assert manifest["manifest_version"] == 3
    assert "action" in manifest
    assert "scripting" in manifest["permissions"]
