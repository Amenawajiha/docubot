"""Common validation helpers used across the app."""
from __future__ import annotations
import re

from slugify import slugify

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def make_slug(value: str) -> str:
    """Convert an arbitrary string into a URL-safe slug."""
    slug = value.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def is_valid_slug(value: str) -> bool:
    return bool(_SLUG_RE.match(value)) and len(value) <= 100


def is_valid_hex_color(value: str) -> bool:
    return bool(re.match(r"^#[0-9A-Fa-f]{6}$", value))

def has_valid_mx(email: str) -> bool:
    try:
        domain = email.split("@")[1]
    except IndexError:
        return False

    import dns.resolver
    import dns.exception

    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(answers) > 0
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
        dns.exception.DNSException,
    ) :
        return False
    