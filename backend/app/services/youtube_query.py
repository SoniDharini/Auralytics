"""Normalize manual creator search input into a YouTube lookup kind.

Does not call YouTube. Invalid video/watch URLs are rejected rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
HANDLE_RE = re.compile(r"^@[\w.-]{2,30}$", re.IGNORECASE)
MIN_NAME_LENGTH = 2

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


@dataclass(frozen=True)
class ParsedCreatorQuery:
    kind: str  # channel_id | handle | username | custom | name
    value: str
    original: str


def parse_manual_creator_query(raw: str) -> ParsedCreatorQuery:
    text = unquote(str(raw or "")).strip()
    if not text:
        raise ValueError("Enter a creator name, @handle, or YouTube channel URL.")

    lowered = text.lower()
    if _looks_like_url(text, lowered):
        return _parse_youtube_url(text)

    compact = text.replace(" ", "")
    if CHANNEL_ID_RE.match(compact):
        return ParsedCreatorQuery(kind="channel_id", value=compact, original=text)

    if text.startswith("@") and len(text.lstrip("@")) >= 2:
        return ParsedCreatorQuery(kind="handle", value=text.lstrip("@"), original=text)

    if len(text) < MIN_NAME_LENGTH:
        raise ValueError("Enter at least 2 characters to search by creator name.")
    return ParsedCreatorQuery(kind="name", value=text, original=text)


def _looks_like_url(text: str, lowered: str) -> bool:
    if "://" in text or lowered.startswith("www.") or lowered.startswith("youtube.com") or lowered.startswith("youtu.be"):
        return True
    return any(host in lowered for host in ("youtube.com/", "youtu.be/"))


def _parse_youtube_url(text: str) -> ParsedCreatorQuery:
    candidate = text.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if host not in _YOUTUBE_HOSTS:
        raise ValueError("Enter a valid YouTube channel URL.")

    path = unquote(parsed.path or "").strip("/")
    parts = [p for p in path.split("/") if p]
    query = parse_qs(parsed.query or "")

    if host.endswith("youtu.be"):
        raise ValueError("That looks like a video link, not a YouTube channel URL.")

    if not parts:
        raise ValueError("Enter a valid YouTube channel URL.")

    first = parts[0].lower()
    if first in {"watch", "shorts", "embed", "live", "playlist", "results"}:
        raise ValueError("That looks like a video or playlist link, not a YouTube channel URL.")
    if query.get("v") and first == "watch":
        raise ValueError("That looks like a video link, not a YouTube channel URL.")

    if first == "channel" and len(parts) >= 2:
        channel_id = parts[1]
        if not CHANNEL_ID_RE.match(channel_id):
            raise ValueError("That YouTube channel ID is not valid.")
        return ParsedCreatorQuery(kind="channel_id", value=channel_id, original=text)

    if first == "user" and len(parts) >= 2:
        username = parts[1].lstrip("@")
        if len(username) < 2:
            raise ValueError("That YouTube channel URL is not valid.")
        return ParsedCreatorQuery(kind="username", value=username, original=text)

    if first == "c" and len(parts) >= 2:
        custom = parts[1].lstrip("@")
        if len(custom) < 2:
            raise ValueError("That YouTube channel URL is not valid.")
        return ParsedCreatorQuery(kind="custom", value=custom, original=text)

    if first.startswith("@"):
        handle = first.lstrip("@")
        if len(handle) < 2:
            raise ValueError("That YouTube handle is not valid.")
        return ParsedCreatorQuery(kind="handle", value=handle, original=text)

    # Bare custom URL path, e.g. youtube.com/carryminati
    if len(parts) == 1 and first not in {"feed", "account", "premium"}:
        token = parts[0].lstrip("@")
        if CHANNEL_ID_RE.match(token):
            return ParsedCreatorQuery(kind="channel_id", value=token, original=text)
        return ParsedCreatorQuery(kind="custom", value=token, original=text)

    raise ValueError("Enter a valid YouTube channel URL.")
