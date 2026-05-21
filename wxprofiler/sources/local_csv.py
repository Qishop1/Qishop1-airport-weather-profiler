from __future__ import annotations

import csv
from pathlib import Path


def read_local_csv(path: str) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row.setdefault("_source", "local_csv")
    return rows
