import os
import ssl
from urllib.parse import urlsplit, urlunsplit, quote

import certifi


def normalize_database_url(url: str) -> str:
    if not url:
        return url

    normalized = url
    if normalized.startswith("postgres://"):
        normalized = "postgresql+asyncpg://" + normalized[len("postgres://"):]
    elif normalized.startswith("postgresql://"):
        normalized = "postgresql+asyncpg://" + normalized[len("postgresql://"):]

    parts = urlsplit(normalized)
    scheme = parts.scheme
    if scheme == "postgresql":
        scheme = "postgresql+asyncpg"

    username = parts.username
    password = parts.password
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    netloc = ""
    if username:
        netloc = quote(username, safe="")
        if password is not None:
            netloc += ":" + quote(password, safe="")
        netloc += "@"
    netloc += host
    if parts.port:
        netloc += f":{parts.port}"

    return urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))


def build_connect_args(
    url: str,
    base_args: dict | None = None,
    disable_ssl_verify: bool | None = None,
) -> dict:
    args = dict(base_args) if base_args else {}
    if not url:
        return args
    host = urlsplit(url).hostname
    if host and (host.endswith(".supabase.co") or host.endswith(".supabase.com")):
        if disable_ssl_verify is None:
            disable_verify = os.getenv("SUPABASE_SSL_NO_VERIFY", "").strip().lower() in {"1", "true", "yes"}
        else:
            disable_verify = disable_ssl_verify
        if disable_verify:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        else:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        args.setdefault("ssl", ssl_context)
    if host and host.endswith(".pooler.supabase.com"):
        args.setdefault("statement_cache_size", 0)
    return args
