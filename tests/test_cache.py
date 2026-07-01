import time

import pytest


@pytest.fixture
def cache(monkeypatch):
    import cache as cache_mod

    monkeypatch.setattr(cache_mod, "CACHE_MODE", "disk")
    return cache_mod


def test_disk_round_trip(cache):
    cache.set_cache("rt_key", {"a": 1})
    assert cache.get_cache("rt_key") == {"a": 1}


def test_disk_missing_key_returns_none(cache):
    assert cache.get_cache("does_not_exist_key") is None


def test_per_entry_ttl_expiry(cache):
    cache.set_cache("ttl_key", {"b": 2}, ttl=0)  # already expired
    assert cache.get_cache("ttl_key") is None


def test_per_entry_ttl_still_valid(cache):
    cache.set_cache("ttl_key2", {"b": 2}, ttl=60)
    assert cache.get_cache("ttl_key2") == {"b": 2}


def test_expired_entry_is_removed(cache, monkeypatch):
    cache.set_cache("stale", {"v": 1}, ttl=10)
    # jump forward in time past the TTL
    real = time.time()
    monkeypatch.setattr(cache.time, "time", lambda: real + 100)
    assert cache.get_cache("stale") is None
    # reading it again (now that the file is gone) is still safe
    assert cache.get_cache("stale") is None


def test_mode_none_disables_cache(cache, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_MODE", "none")
    cache.set_cache("noop", {"x": 1})
    assert cache.get_cache("noop") is None


def test_memcache_without_client_falls_back_to_disk(cache, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_MODE", "memcache")
    monkeypatch.setattr(cache, "memcache_client", None)
    cache.set_cache("fb_key", {"y": 2})
    assert cache.get_cache("fb_key") == {"y": 2}
