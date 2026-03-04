import ipaddress
import socket
from urllib.parse import urlsplit

from ..core.urls import normalize_url

BLOCKED_HOSTNAMES = {"localhost"}


class SSRFValidationError(ValueError):
    pass


def validate_public_url(url: str) -> str:
    normalized_url = normalize_url(url)
    parsed = urlsplit(normalized_url)
    hostname = parsed.hostname

    if not hostname:
        raise SSRFValidationError("url must include hostname")
    if _is_blocked_hostname(hostname):
        raise SSRFValidationError(f"blocked hostname: {hostname}")

    try:
        addrinfo = socket.getaddrinfo(hostname, parsed.port or _default_port(parsed.scheme), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFValidationError(f"failed to resolve hostname: {hostname}") from exc

    resolved_addresses = {_extract_ip(record) for record in addrinfo}
    for address in resolved_addresses:
        if _is_blocked_ip(address):
            raise SSRFValidationError(f"blocked ip address: {address}")

    return normalized_url


def _is_blocked_hostname(hostname: str) -> bool:
    value = hostname.strip(".").lower()
    return value in BLOCKED_HOSTNAMES or value.endswith(".localhost") or value.endswith(".local")


def _extract_ip(addrinfo_row: tuple) -> str:
    sockaddr = addrinfo_row[4]
    if not sockaddr:
        raise SSRFValidationError("hostname resolved without socket address")
    return str(sockaddr[0])


def _is_blocked_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError as exc:
        raise SSRFValidationError(f"invalid ip address from resolver: {value}") from exc
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _default_port(scheme: str) -> int:
    if scheme == "https":
        return 443
    return 80
