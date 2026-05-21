from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen


USER_AGENT = "airport-weather-profiler/0.1 (+https://github.com/)"


def fetch_text(url: str, cache_path: Path, timeout: int = 120, force: bool = False) -> str:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    cache_path.write_text(text, encoding="utf-8")
    return text


def fetch_bytes(url: str, cache_path: Path, timeout: int = 120, force: bool = False) -> bytes:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not force:
        return cache_path.read_bytes()
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    cache_path.write_bytes(raw)
    return raw
