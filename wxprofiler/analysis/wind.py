from __future__ import annotations

import math


def angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def wind_sector(direction: float | None, size: int = 20) -> int | None:
    if direction is None:
        return None
    return int(round(direction / size) * size) % 360


def components(wind_from: float | None, wind_speed: float | None, runway_heading: float) -> dict[str, float | None]:
    if wind_from is None or wind_speed is None:
        return {"headwind": None, "tailwind": None, "crosswind": None}
    diff = math.radians(angle_diff(wind_from, runway_heading))
    signed_headwind = wind_speed * math.cos(diff)
    crosswind = abs(wind_speed * math.sin(diff))
    return {
        "headwind": max(signed_headwind, 0.0),
        "tailwind": max(-signed_headwind, 0.0),
        "crosswind": crosswind,
    }
