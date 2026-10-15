from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_KEYS = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    value = value or utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_url(value: str | None) -> str:
    try:
        raw = (value or "").strip()
        parts = urlsplit(raw)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return ""
        host = parts.hostname.lower()
        port = parts.port
        default_port = (parts.scheme.lower() == "https" and port == 443) or (parts.scheme.lower() == "http" and port == 80)
        netloc = host if not port or default_port else f"{host}:{port}"
        path = re.sub(r"/{2,}", "/", parts.path or "/")
        if len(path) > 1:
            path = path.rstrip("/")
        query = sorted(
            (key, val)
            for key, val in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in TRACKING_KEYS and not key.lower().startswith("utm_")
        )
        return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))
    except (TypeError, ValueError):
        return ""


def plain_text(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalized_text(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", plain_text(value)).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def stable_hash(*parts: object, length: int = 64) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    import email.utils

    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def title_dedupe_key(title: str, published_at: str | None) -> str:
    normalized = normalized_text(title)
    day = (published_at or "")[:10]
    return stable_hash(normalized, day)


def atomic_write(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)
    return target


def write_json(path: str | Path, value: object) -> Path:
    return atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
