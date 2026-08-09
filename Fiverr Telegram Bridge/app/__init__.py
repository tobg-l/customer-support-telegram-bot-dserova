"""Forces IPv4-only DNS resolution for this process.

The VPS this runs on has broken IPv6 routing: imap.gmail.com resolves to both
an AAAA (IPv6) and A (IPv4) record, the IPv6 address is unreachable, and the
default resolution order tries IPv6 first - each failed IPv6 address burns a
full socket timeout (~30s) before falling back to the working IPv4 address,
turning every IMAP connection into a 60s+ stall. Patching socket.getaddrinfo
to only ever return IPv4 results fixes this for imaplib/smtplib and any other
stdlib-based networking in the process (must run before those modules connect,
hence living in the package's __init__ so it's applied on first `import app`).
"""
import socket

_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _ipv4_only_getaddrinfo
