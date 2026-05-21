from __future__ import annotations

import csv
import gzip
import io
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from .cache import fetch_bytes, fetch_text

ISD_HISTORY_CSV = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
ISD_DATA_URL = "https://www.ncei.noaa.gov/pub/data/noaa/{year}/{usaf}-{wban}-{year}.gz"


class NoaaIsdError(RuntimeError):
    pass


class NoaaIsdStationNotFound(NoaaIsdError):
    pass


@dataclass(slots=True)
class IsdStation:
    usaf: str
    wban: str
    name: str | None = None
    country: str | None = None
    state: str | None = None
    icao: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    begin: str | None = None
    end: str | None = None
    distance_km: float | None = None

    @property
    def id(self) -> str:
        return f"{self.usaf}-{self.wban}"

    def to_dict(self) -> dict[str, object]:
        return {
            "usaf": self.usaf,
            "wban": self.wban,
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "state": self.state,
            "icao": self.icao,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "begin": self.begin,
            "end": self.end,
            "distance_km": self.distance_km,
        }


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _station_from_row(row: dict[str, str]) -> IsdStation:
    # NCEI isd-history.csv headers are normally:
    # USAF, WBAN, STATION NAME, CTRY, STATE, ICAO, LAT, LON, ELEV(M), BEGIN, END
    def get(*names: str) -> str | None:
        for name in names:
            if name in row and str(row[name]).strip():
                return str(row[name]).strip()
        return None

    return IsdStation(
        usaf=(get("USAF", "usaf") or "").zfill(6),
        wban=(get("WBAN", "wban") or "").zfill(5),
        name=get("STATION NAME", "station_name", "NAME"),
        country=get("CTRY", "country"),
        state=get("STATE", "state"),
        icao=(get("ICAO", "CALL", "call") or "").upper() or None,
        latitude=_to_float(get("LAT", "latitude")),
        longitude=_to_float(get("LON", "longitude")),
        elevation_m=_to_float(get("ELEV(M)", "ELEV", "elevation_m")),
        begin=get("BEGIN", "begin"),
        end=get("END", "end"),
    )


def station_history(cache_dir: Path, force: bool = False) -> list[IsdStation]:
    text = fetch_text(ISD_HISTORY_CSV, cache_dir / "noaa_isd" / "isd-history.csv", force=force)
    reader = csv.DictReader(io.StringIO(text))
    return [_station_from_row(row) for row in reader if row.get("USAF") and row.get("WBAN")]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _date_in_range(station: IsdStation, start: date, end: date) -> bool:
    def parse_yyyymmdd(s: str | None) -> date | None:
        if not s or len(s) < 8:
            return None
        try:
            return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            return None

    begin = parse_yyyymmdd(station.begin)
    finish = parse_yyyymmdd(station.end)
    if begin and begin > end:
        return False
    if finish and finish < start:
        return False
    return True


def resolve_station(
    station_or_icao: str,
    start: date,
    end: date,
    cache_dir: Path,
    *,
    force: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> IsdStation:
    code = station_or_icao.upper().strip()
    stations = station_history(cache_dir, force=force)
    active = [s for s in stations if _date_in_range(s, start, end)]

    # Direct NOAA station id support: 474340-99999 or 47434099999.
    m = re.fullmatch(r"(\d{6})[- ]?(\d{5})", code)
    if m:
        usaf, wban = m.group(1), m.group(2)
        for s in active:
            if s.usaf == usaf and s.wban == wban:
                return s
        raise NoaaIsdStationNotFound(f"NOAA ISD station {usaf}-{wban} was not found for requested period.")

    exact = [s for s in active if (s.icao or "").upper() == code]
    # Prefer non-missing WBAN/station records, then longest available end date.
    if exact:
        exact.sort(key=lambda s: (s.wban == "99999", s.end or ""))
        return exact[0]

    if latitude is not None and longitude is not None:
        candidates = [s for s in active if s.latitude is not None and s.longitude is not None]
        for s in candidates:
            s.distance_km = _haversine_km(latitude, longitude, s.latitude, s.longitude)  # type: ignore[arg-type]
        candidates.sort(key=lambda s: s.distance_km if s.distance_km is not None else 999999)
        if candidates and (candidates[0].distance_km or 999999) <= 75:
            return candidates[0]

    raise NoaaIsdStationNotFound(
        f"No NOAA ISD station matched ICAO {code}. Provide a config YAML with latitude/longitude, "
        "or use the NOAA station id form USAF-WBAN."
    )


def _int_or_none(text: str, missing: set[str]) -> int | None:
    if text in missing:
        return None
    try:
        return int(text)
    except Exception:
        return None


def _scaled(value: int | None, scale: float) -> float | None:
    return None if value is None else value / scale


def _parse_optional_weather(additional: str) -> tuple[list[str], dict[str, object]]:
    tokens: list[str] = []
    extra: dict[str, object] = {}

    # MWn/AWn present-weather fields carry WMO-style present-weather codes.
    # This broad mapping is intentionally conservative; it is used for coarse
    # climatology, not for reconstructing exact METAR text.
    codes: list[int] = []
    for match in re.finditer(r"(?:MW|AW)[1-9]([0-9]{2})", additional):
        try:
            codes.append(int(match.group(1)))
        except Exception:
            pass
    if codes:
        extra["present_weather_codes"] = codes

    for code in codes:
        if 10 <= code <= 12:
            tokens.append("BR")
        elif 40 <= code <= 49:
            tokens.append("FG")
        elif 50 <= code <= 59:
            tokens.append("DZ")
        elif 60 <= code <= 69:
            tokens.append("RA")
        elif 70 <= code <= 79:
            tokens.append("SN")
        elif 80 <= code <= 84:
            tokens.append("SHRA")
        elif 85 <= code <= 86:
            tokens.append("SHSN")
        elif 87 <= code <= 90:
            tokens.append("GR")
        elif 91 <= code <= 99:
            tokens.append("TS")

    # AA1/AA2/etc precipitation groups: identifier + period(2) + depth(4) + condition(1) + qc(1).
    precip_depths_mm: list[float] = []
    for match in re.finditer(r"AA[1-4]([0-9]{2})([0-9]{4})([0-9])([0-9])", additional):
        depth = match.group(2)
        if depth != "9999":
            try:
                mm = int(depth) / 10.0
                if mm > 0:
                    precip_depths_mm.append(mm)
            except Exception:
                pass
    if precip_depths_mm:
        extra["precip_depths_mm"] = precip_depths_mm
        if not any(t in tokens for t in ["RA", "SN", "DZ", "SHRA", "SHSN"]):
            tokens.append("RA")

    return sorted(set(tokens)), extra


def parse_isd_line(line: str, fallback_station: str | None = None) -> dict[str, object] | None:
    # Full ISD fixed-width mandatory section. Character ranges below are 0-based Python slices.
    if len(line) < 105:
        return None
    usaf = line[4:10].strip()
    wban = line[10:15].strip()
    datestr = line[15:23]
    timestr = line[23:27]
    try:
        valid = datetime(
            int(datestr[0:4]), int(datestr[4:6]), int(datestr[6:8]), int(timestr[0:2]), int(timestr[2:4]), tzinfo=timezone.utc
        )
    except Exception:
        return None

    lat_i = _int_or_none(line[28:34], {"+99999", "-99999", "999999"})
    lon_i = _int_or_none(line[34:41], {"+999999", "-999999", "9999999"})
    elev_i = _int_or_none(line[46:51], {"+9999", "-9999", "99999"})
    call = line[51:56].strip()

    wind_dir = _int_or_none(line[60:63], {"999"})
    wind_speed_i = _int_or_none(line[65:69], {"9999"})
    ceiling_m_i = _int_or_none(line[70:75], {"99999"})
    visibility_m_i = _int_or_none(line[78:84], {"999999"})
    temp_i = _int_or_none(line[87:92], {"+9999", "-9999", "99999"})
    dew_i = _int_or_none(line[93:98], {"+9999", "-9999", "99999"})
    slp_i = _int_or_none(line[99:104], {"99999"})

    additional = line[105:].strip() if len(line) > 105 else ""
    wx_tokens, extra = _parse_optional_weather(additional)

    station = call or fallback_station or f"{usaf}-{wban}"
    return {
        "station": station.upper(),
        "valid_utc": valid.isoformat(),
        "source_station_id": f"{usaf}-{wban}",
        "latitude": _scaled(lat_i, 1000.0),
        "longitude": _scaled(lon_i, 1000.0),
        "elevation_m": _scaled(elev_i, 1.0),
        "call": call or None,
        "wind_dir_deg": float(wind_dir) if wind_dir is not None and wind_dir <= 360 else None,
        "wind_speed_kt": (_scaled(wind_speed_i, 10.0) * 1.943844 if wind_speed_i is not None else None),
        "visibility_m": float(visibility_m_i) if visibility_m_i is not None else None,
        "ceiling_ft": (float(ceiling_m_i) * 3.28084 if ceiling_m_i is not None and ceiling_m_i < 22000 else None),
        "temperature_c": _scaled(temp_i, 10.0),
        "dewpoint_c": _scaled(dew_i, 10.0),
        "altimeter_hpa": _scaled(slp_i, 10.0),
        "wx_tokens": " ".join(wx_tokens),
        "raw_isd": line.rstrip("\n"),
        "_source": "noaa_isd",
        "_source_quality": "global_hourly_fixed_width",
        "_extra": extra,
    }


def download_year(
    station_or_icao: str,
    year: int,
    start: date,
    end: date,
    cache_dir: Path,
    *,
    force: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict[str, object]]:
    station = resolve_station(station_or_icao, start, end, cache_dir, force=force, latitude=latitude, longitude=longitude)
    url = ISD_DATA_URL.format(year=year, usaf=station.usaf, wban=station.wban)
    path = cache_dir / "noaa_isd" / station.id / f"{station.id}-{year}.gz"
    try:
        raw = fetch_bytes(url, path, force=force)
    except (HTTPError, URLError, FileNotFoundError):
        return []

    rows: list[dict[str, object]] = []
    try:
        text = gzip.decompress(raw).decode("utf-8", errors="replace")
    except Exception:
        text = raw.decode("utf-8", errors="replace")

    for line in text.splitlines():
        parsed = parse_isd_line(line, fallback_station=station.icao or station_or_icao.upper())
        if not parsed:
            continue
        valid_dt = datetime.fromisoformat(str(parsed["valid_utc"]))
        d = valid_dt.date()
        if start <= d <= end:
            parsed["resolved_station"] = station.to_dict()
            rows.append(parsed)
    return rows


def download_range(
    station_or_icao: str,
    start: date,
    end: date,
    cache_dir: Path,
    *,
    force: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in range(start.year, end.year + 1):
        rows.extend(
            download_year(
                station_or_icao,
                year,
                start,
                end,
                cache_dir,
                force=force,
                latitude=latitude,
                longitude=longitude,
            )
        )
    return rows
