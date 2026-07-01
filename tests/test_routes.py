import pytest


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.text == "ok"


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "yt2rss" in r.text


def test_help_served(client):
    assert client.get("/help").status_code == 200


def test_rss_escapes_and_structure(client):
    r = client.get("/_user/handle.rss")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/xml")
    body = r.text
    assert "<title>Cool &amp; &lt;Channel&gt;</title>" in body
    assert "Ep 1 &lt;b&gt;" in body
    assert 'guid isPermaLink="false">yt2rss::abc123DEF45' in body
    assert "/redirect/abc123DEF45.mp4" in body
    # only the avatar_uncropped thumbnail is used, escaped
    assert "<image>http://x/a.jpg?w=1&amp;h=2</image>" in body


def test_rss_valid_xml(client):
    import xml.etree.ElementTree as ET

    body = client.get("/_user/handle.rss").text
    root = ET.fromstring(body)
    assert root.tag == "rss"
    assert root.find("./channel/item/enclosure") is not None


@pytest.mark.parametrize(
    "path",
    ["_user/handle", "@handle", "c/Name", "channel/UC123", "user/Name", "Something"],
)
def test_dynamic_rss_paths_resolve(client, path):
    assert client.get(f"/{path}.rss").status_code == 200


def test_playlist_rss(client):
    assert client.get("/playlist.rss?list=PL123").status_code == 200


@pytest.mark.parametrize("bad", ["x", "'inject", "a b", "a" * 21])
def test_video_endpoints_reject_bad_id(client, bad):
    assert client.get(f"/redirect/{bad}.mp4").status_code == 400
    assert client.get(f"/video/{bad}.mp4").status_code == 400


def test_video_endpoint_rejects_path_traversal(client):
    # %2f decodes to '/', so the single-segment route never matches (404),
    # which is also a safe rejection.
    assert client.get("/redirect/..%2f..%2fetc.mp4").status_code in (400, 404)


def test_video_rejects_oversized(client, monkeypatch):
    from api import core

    monkeypatch.setattr(core, "MAX_VIDEO_BYTES", 1000)
    monkeypatch.setattr(
        core,
        "yt_extract_info_video",
        lambda vid, opts=None: {
            "title": "big",
            "formats": [
                {
                    "vcodec": "h264",
                    "acodec": "aac",
                    "ext": "mp4",
                    "height": 720,
                    "url": "http://example/v.mp4",
                    "filesize": 5000,
                }
            ],
        },
    )
    assert client.get("/video/abc123DEF45.mp4").status_code == 413


def test_extraction_failure_returns_400(client, monkeypatch):
    from api import core

    def boom(url, opts=None):
        raise RuntimeError("no network")

    monkeypatch.setattr(core, "yt_extract_info_url", boom)
    assert client.get("/@handle.rss").status_code == 400
