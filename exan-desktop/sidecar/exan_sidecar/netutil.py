"""Network helpers for the phone upload bridge."""

from __future__ import annotations

import ipaddress
import socket

_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def is_lan_client(host: str) -> bool:
    """True for loopback, private, link-local and carrier-grade NAT addresses (never public ones)."""
    try:
        address = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if address.is_loopback or address.is_link_local:
        return True
    if isinstance(address, ipaddress.IPv4Address) and address in _CGNAT:
        return True
    return address.is_private and not address.is_unspecified and not address.is_multicast


def _usable(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if not isinstance(ip, ipaddress.IPv4Address) or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
        return False
    return ip.is_private or ip in _CGNAT


def lan_addresses() -> list[str]:
    """IPv4 addresses a phone on the same Wi-Fi can use to reach this computer, best guess first."""
    found: list[str] = []
    # The interface used for the default route is the best candidate. No packet is sent for UDP connect.
    for probe in ("192.168.0.1", "10.255.255.255", "172.16.0.1"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((probe, 9))
                address = sock.getsockname()[0]
        except OSError:
            continue
        if _usable(address) and address not in found:
            found.append(address)
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        infos = []
    for info in infos:
        address = str(info[4][0])
        if _usable(address) and address not in found:
            found.append(address)

    def rank(address: str) -> int:
        if address.startswith("192.168."):
            return 0
        if address.startswith("10."):
            return 1
        if address.startswith("172."):
            return 2
        return 3

    primary = found[:1]
    return primary + sorted(found[1:], key=rank)
