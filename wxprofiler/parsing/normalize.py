from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from wxprofiler.model import Observation
from wxprofiler.timeutil import parse_utc, to_local

WX_TOKEN_RE = re.compile(r"(?:^|\s)([-+]?VC)?(?:MI|PR|BC|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)(?=\s|$)")
CEILING_COVERS = {"BKN", "OVC", "VV"}


def f(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"M", "NA", "NAN", "NONE", "NULL"}:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def normalize_iem(row: dict[str, str], timezone_name: str | None) -> Observation:
    station = (row.get("station") or row.get("station_id") or "").upper()
    valid = parse_utc(row["valid"])
    clouds = []
    for i in range(1, 4):
        cover = (row.get(f"skyc{i}") or "").strip().upper() or None
        base = f(row.get(f"skyl{i}"))
        if cover or base is not None:
            clouds.append((cover, base))
    obs = Observation(
        station=station,
        valid_utc=valid,
        valid_local=to_local(valid, timezone_name),
        raw_metar=row.get("metar") or None,
        source="iem_asos",
        source_quality="metar_asos",
        wind_dir_deg=f(row.get("drct")),
        wind_speed_kt=f(row.get("sknt")),
        wind_gust_kt=f(row.get("gust")),
        visibility_m=(f(row.get("vsby")) * 1609.344 if f(row.get("vsby")) is not None else None),
        altimeter_hpa=(f(row.get("alti")) * 33.8638866667 if f(row.get("alti")) is not None else None),
        temperature_c=f(row.get("tmpc")),
        dewpoint_c=f(row.get("dwpc")),
        relative_humidity=f(row.get("relh")),
        clouds=clouds,
        wx_tokens=parse_wx_tokens(row.get("wxcodes") or row.get("metar") or ""),
    )
    obs.ceiling_ft = compute_ceiling(obs.clouds)
    return obs


def normalize_local(row: dict[str, str], station: str, timezone_name: str | None) -> Observation:
    valid_str = row.get("valid_utc") or row.get("valid") or row.get("time") or row.get("date")
    if not valid_str:
        raise ValueError("Local CSV row has no valid_utc/valid/time/date column")
    valid = parse_utc(valid_str)
    clouds = []
    for i in range(1, 4):
        cover = (row.get(f"cloud_{i}_cover") or row.get(f"skyc{i}") or "").strip().upper() or None
        base = f(row.get(f"cloud_{i}_base_ft") or row.get(f"skyl{i}"))
        if cover or base is not None:
            clouds.append((cover, base))
    obs = Observation(
        station=(row.get("station") or station).upper(),
        valid_utc=valid,
        valid_local=to_local(valid, timezone_name),
        raw_metar=row.get("raw_metar") or row.get("metar"),
        source=row.get("_source", "local_csv"),
        source_quality="user_supplied",
        wind_dir_deg=f(row.get("wind_dir_deg") or row.get("drct")),
        wind_speed_kt=f(row.get("wind_speed_kt") or row.get("sknt")),
        wind_gust_kt=f(row.get("wind_gust_kt") or row.get("gust")),
        visibility_m=f(row.get("visibility_m")) or (f(row.get("vsby")) * 1609.344 if f(row.get("vsby")) is not None else None),
        altimeter_hpa=f(row.get("altimeter_hpa")),
        temperature_c=f(row.get("temperature_c") or row.get("tmpc")),
        dewpoint_c=f(row.get("dewpoint_c") or row.get("dwpc")),
        relative_humidity=f(row.get("relative_humidity") or row.get("relh")),
        clouds=clouds,
        wx_tokens=parse_wx_tokens(row.get("wx_tokens") or row.get("wxcodes") or row.get("raw_metar") or row.get("metar") or ""),
    )
    obs.ceiling_ft = f(row.get("ceiling_ft")) or compute_ceiling(obs.clouds)
    return obs


def normalize_meteostat(row: dict[str, str], station: str, timezone_name: str | None) -> Observation:
    # Meteostat hourly bulk is not METAR-native. It is useful for climate statistics,
    # but weather-code and cloud detail may be weaker than IEM METAR.
    ts = row.get("time") or row.get("date")
    if not ts:
        raise ValueError("Meteostat row has no time/date column")
    valid = parse_utc(ts)
    obs = Observation(
        station=station.upper(),
        valid_utc=valid,
        valid_local=to_local(valid, timezone_name),
        source="meteostat",
        source_quality="normalized_hourly_non_metar",
        wind_dir_deg=f(row.get("wdir")),
        wind_speed_kt=(f(row.get("wspd")) * 0.539957 if f(row.get("wspd")) is not None else None),
        wind_gust_kt=(f(row.get("wpgt")) * 0.539957 if f(row.get("wpgt")) is not None else None),
        visibility_m=f(row.get("vis")),
        altimeter_hpa=f(row.get("pres")),
        temperature_c=f(row.get("temp")),
        dewpoint_c=f(row.get("dwpt")),
        relative_humidity=f(row.get("rhum")),
        wx_tokens=[],
    )
    return obs


def compute_ceiling(clouds: list[tuple[str | None, float | None]]) -> float | None:
    bases = [base for cover, base in clouds if cover in CEILING_COVERS and base is not None]
    return min(bases) if bases else None


def parse_wx_tokens(text: str) -> list[str]:
    if not text:
        return []
    tokens: list[str] = []
    for part in text.replace(",", " ").split():
        p = part.strip().upper()
        if not p:
            continue
        # Preserve common METAR weather tokens and IEM compound tokens.
        if any(code in p for code in ["RA", "SN", "FG", "BR", "TS", "FZ", "DZ", "SH", "BL", "HZ", "FU", "GR", "PL"]):
            tokens.append(p)
    if tokens:
        return tokens
    return [m.group(0).strip() for m in WX_TOKEN_RE.finditer(text.upper())]


def normalize_noaa_isd(row: dict[str, object], station: str, timezone_name: str | None) -> Observation:
    valid_str = str(row.get("valid_utc") or row.get("valid") or "")
    if not valid_str:
        raise ValueError("NOAA ISD row has no valid_utc column")
    valid = parse_utc(valid_str)
    ceiling = f(row.get("ceiling_ft"))
    clouds = [("BKN", ceiling)] if ceiling is not None else []
    wx_text = str(row.get("wx_tokens") or "")
    obs = Observation(
        station=(str(row.get("station") or station)).upper(),
        valid_utc=valid,
        valid_local=to_local(valid, timezone_name),
        raw_metar=str(row.get("raw_isd") or "") or None,
        source="noaa_isd",
        source_quality=str(row.get("_source_quality") or "global_hourly_fixed_width"),
        wind_dir_deg=f(row.get("wind_dir_deg")),
        wind_speed_kt=f(row.get("wind_speed_kt")),
        wind_gust_kt=f(row.get("wind_gust_kt")),
        visibility_m=f(row.get("visibility_m")),
        altimeter_hpa=f(row.get("altimeter_hpa")),
        temperature_c=f(row.get("temperature_c")),
        dewpoint_c=f(row.get("dewpoint_c")),
        relative_humidity=f(row.get("relative_humidity")),
        clouds=clouds,
        ceiling_ft=ceiling,
        wx_tokens=parse_wx_tokens(wx_text),
        extra={
            "source_station_id": row.get("source_station_id"),
            "resolved_station": row.get("resolved_station"),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "elevation_m": row.get("elevation_m"),
        },
    )
    return obs
