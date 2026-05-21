from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Runway:
    id: str
    heading: float


@dataclass(slots=True)
class AirportConfig:
    airport: str
    timezone: str | None = None
    runways: list[Runway] = field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None


def load_runway_config(path: str | None, airport: str) -> AirportConfig:
    if not path:
        return AirportConfig(airport=airport.upper())
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        return AirportConfig(
            airport=str(data.get("airport", airport)).upper(),
            timezone=data.get("timezone"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            elevation_m=data.get("elevation_m"),
            runways=[Runway(id=str(r["id"]), heading=float(r["heading"])) for r in data.get("runways", [])],
        )
    except Exception:
        return _parse_minimal_yaml(text, airport)


def _parse_minimal_yaml(text: str, airport: str) -> AirportConfig:
    cfg = AirportConfig(airport=airport.upper())
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s*-\s*", line):
            if current:
                cfg.runways.append(Runway(id=current.get("id", ""), heading=float(current.get("heading", "0"))))
            current = {}
            line = re.sub(r"^\s*-\s*", "", line)
            if line:
                k, v = _kv(line)
                current[k] = v
            continue
        if current is not None and raw.startswith(" "):
            k, v = _kv(line.strip())
            current[k] = v
            continue
        if current:
            cfg.runways.append(Runway(id=current.get("id", ""), heading=float(current.get("heading", "0"))))
            current = None
        k, v = _kv(line.strip())
        if k == "airport":
            cfg.airport = v.upper()
        elif k == "timezone":
            cfg.timezone = v
        elif k == "latitude":
            cfg.latitude = float(v)
        elif k == "longitude":
            cfg.longitude = float(v)
        elif k == "elevation_m":
            cfg.elevation_m = float(v)
    if current:
        cfg.runways.append(Runway(id=current.get("id", ""), heading=float(current.get("heading", "0"))))
    return cfg


def _kv(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Invalid config line: {line}")
    k, v = line.split(":", 1)
    return k.strip(), v.strip().strip('"').strip("'")
