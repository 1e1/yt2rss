# app/discovery.py
# Optional mDNS / DNS-SD announcement so other LAN services can discover yt2rss.
# Depends only on `settings`; safe to import even when the feature is disabled.
import socket

from settings import (
    MDNS_ENABLED,
    MDNS_NAME,
    MDNS_PORT,
    MDNS_TYPE,
    logger,
)
from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf


def _local_ip() -> str:
    """Best-effort primary LAN IPv4 (no packet is actually sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # TEST-NET-1, unroutable
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class LanAnnouncer:
    """Registers (and cleanly withdraws) an mDNS service for this instance."""

    def __init__(self) -> None:
        self._aiozc: AsyncZeroconf | None = None
        self._info: ServiceInfo | None = None

    async def start(self) -> bool:
        if not MDNS_ENABLED:
            logger.debug("[mdns] disabled")
            return False
        try:
            ip = _local_ip()
            hostname = socket.gethostname().split(".")[0]
            service_name = f"{MDNS_NAME}.{MDNS_TYPE}"
            self._info = ServiceInfo(
                MDNS_TYPE,
                service_name,
                addresses=[socket.inet_aton(ip)],
                port=MDNS_PORT,
                properties={"app": "yt2rss", "path": "/"},
                server=f"{hostname}.local.",
            )
            self._aiozc = AsyncZeroconf()
            await self._aiozc.async_register_service(self._info)
            logger.info(f"[mdns] announced {service_name} at {ip}:{MDNS_PORT}")
            return True
        except Exception as e:
            logger.warning(f"[mdns] could not announce on the LAN: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        if not self._aiozc:
            return
        try:
            if self._info:
                await self._aiozc.async_unregister_service(self._info)
            await self._aiozc.async_close()
        except Exception as e:
            logger.warning(f"[mdns] error during shutdown: {e}")
        finally:
            self._aiozc = None
            self._info = None
