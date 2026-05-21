from __future__ import annotations

import csv
import gzip
import io
import json
from datetime import date
from pathlib import Path

from .cache import fetch_bytes

STATIONS_FULL_URLS = [
    "https://bulk.meteostat.net/v2/stations/full.json.gz",
    "https://data.meteostat.net/stations/full.json.gz",
]


def find_station_by_icao(icao: str, cache_dir: Path, force: bool = False) -> dict | None:
    icao = icao.upper()
    data = None
    last_error: Exception | None = None
    for url in STATIONS_FULL_URLS:
        try:
            raw = fetch_bytes(url, cache_dir / "meteostat" / "stations_full.json.gz", force=force)
            data = json.loads(gzip.decompress(raw).decode("utf-8", errors="replace"))
            break
        except Exception as exc:
            last_error = exc
            continue
    if data is None:
        raise RuntimeError(f"Could not download Meteostat station inventory: {last_error}")
    items = data.values() if isinstance(data, dict) else data
    for item in items:
        identifiers = item.get("identifiers") or {}
        candidates = [identifiers.get("icao"), identifiers.get("icao_code"), item.get("icao")]
        if any(str(c).upper() == icao for c in candidates if c):
            return item
    return None


def download_hourly_by_station_id(station_id: str, start: date, end: date, cache_dir: Path, force: bool = False) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in range(start.year, end.year + 1):
        url = f"https://bulk.meteostat.net/v2/hourly/{year}/{station_id}.csv.gz"
        path = cache_dir / "meteostat" / "hourly" / str(year) / f"{station_id}.csv.gz"
        try:
            raw = fetch_bytes(url, path, force=force)
        except Exception:
            continue
        text = gzip.decompress(raw).decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            row["_source"] = "meteostat"
            row["_station_id"] = station_id
            rows.append(row)
    return rows
