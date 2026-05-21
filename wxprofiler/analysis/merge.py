from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from wxprofiler.model import Observation

SOURCE_PRIORITY = {
    "iem_asos": 100,
    "local_csv": 95,
    "noaa_isd": 80,
    "meteostat": 60,
    "unknown": 0,
}


def _quality_score(o: Observation) -> int:
    score = SOURCE_PRIORITY.get(o.source, 0)
    if o.raw_metar:
        score += 10
    if o.wx_tokens:
        score += 6
    if o.ceiling_ft is not None:
        score += 4
    if o.visibility_m is not None:
        score += 3
    if o.wind_dir_deg is not None and o.wind_speed_kt is not None:
        score += 3
    return score


def _slot_key(o: Observation) -> tuple[str, datetime]:
    # Historical airport observations are normally hourly; use exact UTC minute after truncating seconds.
    dt = o.valid_utc.replace(second=0, microsecond=0)
    return (o.station.upper(), dt)


def merge_observations(groups: list[tuple[str, list[Observation]]]) -> tuple[list[Observation], dict[str, Any]]:
    all_obs: list[Observation] = []
    for _, obs in groups:
        all_obs.extend(obs)
    before = len(all_obs)
    by_time: dict[datetime, list[Observation]] = {}
    # Deliberately dedupe by timestamp, not station, because fallback station/call sign may differ for the same airport.
    for o in all_obs:
        dt = o.valid_utc.replace(second=0, microsecond=0)
        by_time.setdefault(dt, []).append(o)

    chosen: list[Observation] = []
    duplicate_count = 0
    replaced_by_source: Counter[str] = Counter()
    for dt, candidates in by_time.items():
        if len(candidates) > 1:
            duplicate_count += len(candidates) - 1
        candidates.sort(key=_quality_score, reverse=True)
        winner = candidates[0]
        winner.extra = dict(winner.extra or {})
        winner.extra["merged_candidate_count"] = len(candidates)
        winner.extra["merged_candidate_sources"] = sorted({c.source for c in candidates})
        chosen.append(winner)
        for loser in candidates[1:]:
            replaced_by_source[loser.source] += 1

    chosen.sort(key=lambda o: o.valid_utc)
    source_counts = Counter(o.source for o in chosen)
    raw_counts = Counter()
    for source, obs in groups:
        raw_counts[source] += len(obs)
    report = {
        "strategy": "timestamp_priority_deduplication",
        "priority": SOURCE_PRIORITY,
        "inputRecords": before,
        "outputRecords": len(chosen),
        "duplicateRecordsRemoved": duplicate_count,
        "inputBySource": dict(sorted(raw_counts.items())),
        "outputBySource": dict(sorted(source_counts.items())),
        "discardedBySource": dict(sorted(replaced_by_source.items())),
    }
    return chosen, report
