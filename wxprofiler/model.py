from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Observation:
    station: str
    valid_utc: datetime
    valid_local: datetime | None = None
    raw_metar: str | None = None
    source: str = "unknown"
    source_quality: str = "raw"
    wind_dir_deg: float | None = None
    wind_speed_kt: float | None = None
    wind_gust_kt: float | None = None
    visibility_m: float | None = None
    altimeter_hpa: float | None = None
    temperature_c: float | None = None
    dewpoint_c: float | None = None
    relative_humidity: float | None = None
    clouds: list[tuple[str | None, float | None]] = field(default_factory=list)
    ceiling_ft: float | None = None
    wx_tokens: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "station": self.station,
            "valid_utc": self.valid_utc.isoformat(),
            "valid_local": self.valid_local.isoformat() if self.valid_local else None,
            "month": self.valid_local.month if self.valid_local else self.valid_utc.month,
            "hour_local": self.valid_local.hour if self.valid_local else self.valid_utc.hour,
            "raw_metar": self.raw_metar,
            "source": self.source,
            "source_quality": self.source_quality,
            "wind_dir_deg": self.wind_dir_deg,
            "wind_speed_kt": self.wind_speed_kt,
            "wind_gust_kt": self.wind_gust_kt,
            "visibility_m": self.visibility_m,
            "altimeter_hpa": self.altimeter_hpa,
            "temperature_c": self.temperature_c,
            "dewpoint_c": self.dewpoint_c,
            "relative_humidity": self.relative_humidity,
            "ceiling_ft": self.ceiling_ft,
            "wx_tokens": " ".join(self.wx_tokens),
        }
        for i in range(3):
            cover, base = self.clouds[i] if i < len(self.clouds) else (None, None)
            row[f"cloud_{i+1}_cover"] = cover
            row[f"cloud_{i+1}_base_ft"] = base
        return row
