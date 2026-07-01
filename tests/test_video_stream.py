"""Integration tests for the /video streaming branch (no network, httpx stubbed)."""

import pytest

VALID_ID = "abc123DEF45"


class _FakeStream:
    def __init__(self, chunks, headers):
        self._chunks = chunks
        self.headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def aiter_bytes(self, size=None):
        for chunk in self._chunks:
            yield chunk


class _FakeAsyncClient:
    def __init__(self, chunks, headers):
        self._chunks = chunks
        self._headers = headers
        self.closed = False

    def stream(self, method, url, follow_redirects=False):
        return _FakeStream(self._chunks, self._headers)

    async def aclose(self):
        self.closed = True


@pytest.fixture
def stub_stream(monkeypatch):
    """Point the /video proxy at an mp4 format and a fake httpx client."""

    def _apply(chunks, headers=None, max_bytes=0):
        from api import core

        monkeypatch.setattr(core, "MAX_VIDEO_BYTES", max_bytes)
        monkeypatch.setattr(
            core,
            "yt_extract_info_video",
            lambda vid, opts=None: {
                "title": "vid",
                "formats": [
                    {
                        "vcodec": "h264",
                        "acodec": "aac",
                        "ext": "mp4",
                        "height": 720,
                        "url": "http://example/v.mp4",
                    }
                ],
            },
        )
        monkeypatch.setattr(
            core.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(chunks, headers or {})
        )

    return _apply


def test_stream_full_body_when_under_limit(client, stub_stream):
    stub_stream([b"a" * 100, b"b" * 100], max_bytes=0)  # unlimited
    r = client.get(f"/video/{VALID_ID}.mp4")
    assert r.status_code == 200
    assert r.content == b"a" * 100 + b"b" * 100
    assert r.headers["content-type"].startswith("video/mp4")


def test_stream_truncates_when_exceeding_limit(client, stub_stream):
    # 5x100B chunks, cap 250B -> stops before the chunk that would cross the cap.
    stub_stream([b"x" * 100] * 5, max_bytes=250)
    r = client.get(f"/video/{VALID_ID}.mp4")
    assert r.status_code == 200
    assert len(r.content) == 200  # only the first two chunks were delivered


def test_stream_stops_on_oversized_content_length(client, stub_stream):
    stub_stream([b"z" * 100], headers={"content-length": "999999"}, max_bytes=1000)
    r = client.get(f"/video/{VALID_ID}.mp4")
    assert r.status_code == 200
    assert r.content == b""  # rejected before any chunk was streamed
