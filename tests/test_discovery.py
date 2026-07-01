"""Tests for the optional mDNS LAN announcement (zeroconf stubbed, no network)."""

import asyncio


class _FakeAioZC:
    def __init__(self):
        self.registered = None
        self.unregistered = None
        self.closed = False

    async def async_register_service(self, info):
        self.registered = info

    async def async_unregister_service(self, info):
        self.unregistered = info

    async def async_close(self):
        self.closed = True


def test_disabled_is_noop():
    import discovery

    ann = discovery.LanAnnouncer()
    assert asyncio.run(ann.start()) is False
    # stop() on a never-started announcer must be safe
    asyncio.run(ann.stop())


def test_announce_registers_and_unregisters(monkeypatch):
    import discovery

    monkeypatch.setattr(discovery, "MDNS_ENABLED", True)
    monkeypatch.setattr(discovery, "_local_ip", lambda: "10.0.0.5")
    monkeypatch.setattr(discovery, "AsyncZeroconf", _FakeAioZC)

    ann = discovery.LanAnnouncer()
    assert asyncio.run(ann.start()) is True

    zc = ann._aiozc
    assert zc.registered is not None
    assert zc.registered.port == discovery.MDNS_PORT
    assert discovery.MDNS_NAME in zc.registered.name

    asyncio.run(ann.stop())
    assert zc.unregistered is not None
    assert zc.closed is True
    assert ann._aiozc is None


def test_announce_failure_is_swallowed(monkeypatch):
    import discovery

    def boom():
        raise RuntimeError("no multicast available")

    monkeypatch.setattr(discovery, "MDNS_ENABLED", True)
    monkeypatch.setattr(discovery, "_local_ip", lambda: "10.0.0.5")
    monkeypatch.setattr(discovery, "AsyncZeroconf", lambda *a, **k: boom())

    ann = discovery.LanAnnouncer()
    assert asyncio.run(ann.start()) is False  # never raises, degrades gracefully


def test_local_ip_returns_string():
    import discovery

    ip = discovery._local_ip()
    assert isinstance(ip, str) and ip.count(".") == 3
