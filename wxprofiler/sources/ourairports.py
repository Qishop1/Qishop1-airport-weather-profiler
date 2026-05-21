from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import fetch_text
from wxprofiler.config import AirportConfig, Runway

OURAIRPORTS_AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_RUNWAYS_URL = "https://davidmegginson.github.io/ourairports-data/runways.csv"


@dataclass(slots=True)
class AirportRecord:
    ident: str
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_ft: float | None = None
    iso_country: str | None = None
    municipality: str | None = None


def _float(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _read_csv_text(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def load_airports(cache_dir: Path, force: bool = False) -> list[dict[str, str]]:
    text = fetch_text(OURAIRPORTS_AIRPORTS_URL, cache_dir / "ourairports" / "airports.csv", force=force)
    return _read_csv_text(text)


def load_runways(cache_dir: Path, force: bool = False) -> list[dict[str, str]]:
    text = fetch_text(OURAIRPORTS_RUNWAYS_URL, cache_dir / "ourairports" / "runways.csv", force=force)
    return _read_csv_text(text)


def find_airport(icao: str, cache_dir: Path, force: bool = False) -> AirportRecord | None:
    icao = icao.upper().strip()
    for row in load_airports(cache_dir, force=force):
        ident = (row.get("ident") or "").upper()
        gps = (row.get("gps_code") or "").upper()
        local = (row.get("local_code") or "").upper()
        iata = (row.get("iata_code") or "").upper()
        if icao in {ident, gps, local, iata}:
            return AirportRecord(
                ident=ident or icao,
                name=row.get("name") or None,
                latitude=_float(row.get("latitude_deg")),
                longitude=_float(row.get("longitude_deg")),
                elevation_ft=_float(row.get("elevation_ft")),
                iso_country=row.get("iso_country") or None,
                municipality=row.get("municipality") or None,
            )
    return None


def _magnetic_heading_from_ident(ident: str) -> float | None:
    digits = "".join(ch for ch in ident if ch.isdigit())
    if not digits:
        return None
    try:
        n = int(digits[:2])
        if 1 <= n <= 36:
            return float(360 if n == 36 else n * 10)
    except Exception:
        return None
    return None


def _runway_heading(row: dict[str, str], side: str) -> float | None:
    ident = (row.get(f"{side}_ident") or "").strip().upper()
    # For operational tailwind/crosswind analysis, runway number is usually safer because
    # it represents the published magnetic runway direction. OurAirports heading_degT
    # is often true heading; using it directly can be wrong at airports with large
    # magnetic variation, e.g. RJCC 01/19 appearing as 353/173 true.
    magnetic = _magnetic_heading_from_ident(ident)
    if magnetic is not None:
        return magnetic
    for key in [f"{side}_heading_degT", f"{side}_heading_deg", f"{side}_heading"]:
        val = _float(row.get(key))
        if val is not None:
            return round(val % 360, 1)
    return None


def resolve_runways(icao: str, cache_dir: Path, force: bool = False) -> tuple[list[Runway], list[str]]:
    icao = icao.upper().strip()
    warnings: list[str] = []
    rows = load_runways(cache_dir, force=force)
    runways: list[Runway] = []
    seen: set[str] = set()
    for row in rows:
        airport_ident = (row.get("airport_ident") or "").upper()
        if airport_ident != icao:
            continue
        for side in ["le", "he"]:
            ident = (row.get(f"{side}_ident") or "").strip().upper()
            heading = _runway_heading(row, side)
            if not ident or heading is None or ident in seen or ident in {"XX", "XXX"}:
                continue
            seen.add(ident)
            runways.append(Runway(id=ident, heading=heading))
    if runways:
        warnings.append("Runway headings were resolved from runway identifiers where possible. This is better for operational magnetic runway analysis than raw true-heading data, but user YAML is still recommended for high precision.")
    return runways, warnings


def enrich_config_from_ourairports(cfg: AirportConfig, cache_dir: Path, force: bool = False, *, auto_runways: bool = True) -> tuple[AirportConfig, dict[str, Any]]:
    report: dict[str, Any] = {"source": "ourairports", "airportMatched": False, "runwaysMatched": False, "warnings": []}
    rec = find_airport(cfg.airport, cache_dir, force=force)
    if rec:
        report["airportMatched"] = True
        report["airport"] = {
            "ident": rec.ident,
            "name": rec.name,
            "latitude": rec.latitude,
            "longitude": rec.longitude,
            "elevation_ft": rec.elevation_ft,
            "iso_country": rec.iso_country,
            "municipality": rec.municipality,
        }
        if cfg.latitude is None:
            cfg.latitude = rec.latitude
        if cfg.longitude is None:
            cfg.longitude = rec.longitude
        if cfg.elevation_m is None and rec.elevation_ft is not None:
            cfg.elevation_m = round(rec.elevation_ft * 0.3048, 1)
    else:
        report["warnings"].append("Airport was not found in OurAirports airports.csv; latitude/longitude/elevation could not be auto-filled.")

    if auto_runways and not cfg.runways:
        runways, warnings = resolve_runways(cfg.airport, cache_dir, force=force)
        report["warnings"].extend(warnings)
        if runways:
            cfg.runways = runways
            report["runwaysMatched"] = True
            report["runways"] = [{"id": r.id, "heading": r.heading} for r in runways]
        else:
            report["warnings"].append("No runway records were found in OurAirports runways.csv; runway operational statistics will be skipped unless a YAML runway file is supplied.")
    elif cfg.runways:
        report["runwaysMatched"] = True
        report["source"] = "user_yaml_or_supplied"
        report["runways"] = [{"id": r.id, "heading": r.heading} for r in cfg.runways]
    return cfg, report
