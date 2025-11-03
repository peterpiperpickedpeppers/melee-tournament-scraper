#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Write unique archetypes (deck names) from the event pairings CSV to a CSV file.

Outputs:
- <EVENT_DATA_DIR>/<EVENT_NAME> pairings unique archetypes.csv

Environment:
- EVENT_DATA_DIR: path to the event folder under data/
- EVENT_NAME: event name (used to locate files)
"""
from __future__ import annotations
from pathlib import Path
import os
import sys
import pandas as pd


def find_pairings_csv(event_dir: Path, event_name: str | None = None) -> Path | None:
    # Prefer true pairings files: include 'pairings' but exclude derived 'unique archetypes' lists
    candidates = [p for p in event_dir.glob("*pairings*.csv") if "unique archetypes" not in p.name.lower()]
    # If an event_name is provided, further prefer files that start with that name
    if event_name:
        exact = [p for p in candidates if p.name.lower().startswith(event_name.lower())]
        if exact:
            exact = sorted(exact, key=lambda p: p.stat().st_mtime, reverse=True)
            return exact[0]
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    others = sorted(event_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return others[0] if others else None


def write_unique_archetypes() -> int:
    event_data_dir = os.getenv("EVENT_DATA_DIR")
    event_name = os.getenv("EVENT_NAME")
    # Trim whitespace in env vars to avoid path issues
    event_data_dir = event_data_dir.strip() if event_data_dir else event_data_dir
    event_name = event_name.strip() if event_name else event_name
    if not event_data_dir or not event_name:
        print("ERROR: EVENT_DATA_DIR and EVENT_NAME must be set.", file=sys.stderr)
        return 1

    event_dir = Path(event_data_dir)
    if not event_dir.exists():
        print(f"ERROR: Event directory not found: {event_dir}", file=sys.stderr)
        return 1

    pairings_path = find_pairings_csv(event_dir, event_name)
    if pairings_path is None or not pairings_path.exists():
        print(f"ERROR: No pairings CSV found in {event_dir}", file=sys.stderr)
        return 1

    print(f"Loading pairings from: {pairings_path}")
    df = pd.read_csv(pairings_path)

    # Identify deck columns (case-insensitive contains 'deck')
    deck_cols = [c for c in df.columns if 'deck' in c.lower()]
    if not deck_cols:
        print("ERROR: No deck columns found in pairings CSV.", file=sys.stderr)
        return 1

    # Collect unique archetypes from the deck columns
    values = []
    for col in deck_cols:
        values.append(df[col].fillna("").astype(str).str.strip())
    combined = pd.concat(values, ignore_index=True)
    # Use Series.unique() to get unique values from the combined series
    uniques = sorted([v for v in combined.dropna().astype(str).str.strip().unique() if v])

    # Standardize output filename to match existing convention
    out_path = event_dir / f"{event_name} unique archetypes.csv"
    pd.DataFrame({"Archetype": uniques}).to_csv(out_path, index=False)
    print(f"Wrote {len(uniques)} unique archetypes to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(write_unique_archetypes())
