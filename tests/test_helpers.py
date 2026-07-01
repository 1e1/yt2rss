import pytest
from api import core


def test_xml_escape_all_entities():
    assert core.xml_escape("<a>&'\"") == "&lt;a&gt;&amp;&apos;&quot;"


def test_xml_escape_empty_and_none():
    assert core.xml_escape(None) == ""
    assert core.xml_escape("") == ""


def test_sanitize_filename_strips_forbidden_chars():
    assert core.sanitize_filename('a/b:c*?"<>|\\') == "abc"


def test_sanitize_filename_collapses_whitespace_and_truncates():
    assert core.sanitize_filename("  a   b  ") == "a b"
    assert len(core.sanitize_filename("x" * 500)) == 200


def test_choose_combined_mp4_prefers_mp4_at_target_height():
    best = core.choose_combined_mp4(
        [
            {"vcodec": "h264", "acodec": "aac", "ext": "webm", "height": 720},
            {"vcodec": "h264", "acodec": "aac", "ext": "mp4", "height": 720},
            {"vcodec": "h264", "acodec": "aac", "ext": "mp4", "height": 480},
        ],
        720,
    )
    assert best["ext"] == "mp4" and best["height"] == 720


def test_choose_combined_mp4_skips_video_or_audio_only():
    best = core.choose_combined_mp4(
        [
            {"vcodec": "h264", "acodec": "none", "ext": "mp4", "height": 1080},
            {"vcodec": "none", "acodec": "aac", "ext": "m4a", "height": 0},
            {"vcodec": "h264", "acodec": "aac", "ext": "mp4", "height": 360},
        ],
        720,
    )
    assert best["height"] == 360


def test_choose_combined_mp4_empty():
    assert core.choose_combined_mp4([], 720) is None
    assert core.choose_combined_mp4(None, 720) is None


@pytest.mark.parametrize("vid", ["abc123DEF45", "dQw4w9WgXcQ", "aBcDeF"])
def test_validate_video_id_accepts_valid(vid):
    assert core.validate_video_id(vid) == vid


@pytest.mark.parametrize("vid", ["../etc", "a b", "'; rm", "x", "a" * 21, "ab/cd"])
def test_validate_video_id_rejects_invalid(vid):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        core.validate_video_id(vid)
    assert exc.value.status_code == 400


def test_exceeds_limit_disabled_by_default(monkeypatch):
    monkeypatch.setattr(core, "MAX_VIDEO_BYTES", 0)
    assert core._exceeds_limit(10**12) is False


def test_exceeds_limit_enforced(monkeypatch):
    monkeypatch.setattr(core, "MAX_VIDEO_BYTES", 100)
    assert core._exceeds_limit(101) is True
    assert core._exceeds_limit(100) is False
    assert core._exceeds_limit(None) is False
