from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def parse_utc(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_local(dt_utc: datetime, timezone_name: str | None) -> datetime:
    if timezone_name:
        return dt_utc.astimezone(ZoneInfo(timezone_name))
    return dt_utc
