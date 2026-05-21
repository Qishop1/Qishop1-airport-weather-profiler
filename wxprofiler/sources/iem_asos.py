from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from .cache import fetch_text

IEM_ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
IEM_FIELDS = [
    "tmpc", "dwpc", "relh", "drct", "sknt", "gust", "alti", "mslp", "vsby",
    "skyc1", "skyc2", "skyc3", "skyl1", "skyl2", "skyl3", "wxcodes", "metar",
]


def download_year(station: str, year: int, start: date, end: date, cache_dir: Path, force: bool = False) -> list[dict[str, str]]:
    station = station.upper()
    y_start = max(start, date(year, 1, 1))
    y_end = min(end, date(year, 12, 31))
    params = {
        "station": station,
        "data": IEM_FIELDS,
        "year1": y_start.year,
        "month1": y_start.month,
        "day1": y_start.day,
        "year2": y_end.year,
        "month2": y_end.month,
        "day2": y_end.day,
        "tz": "Etc/UTC",
        "format": "onlycomma",
        "latlon": "yes",
        "elev": "yes",
        "missing": "empty",
        "trace": "empty",
        "direct": "yes",
        "report_type": ["1", "2", "3", "4"],
    }
    url = f"{IEM_ASOS_URL}?{urlencode(params, doseq=True)}"
    path = cache_dir / "iem_asos" / station / f"{station}_{year}.csv"
    text = fetch_text(url, path, force=force)
    rows = []
    clean_lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    if not clean_lines:
        return rows
    reader = csv.DictReader(io.StringIO("\n".join(clean_lines)))
    for row in reader:
        if row.get("valid"):
            row["_source"] = "iem_asos"
            rows.append(row)
    return rows


def download_range(station: str, start: date, end: date, cache_dir: Path, force: bool = False) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in range(start.year, end.year + 1):
        rows.extend(download_year(station, year, start, end, cache_dir, force=force))
    return rows
