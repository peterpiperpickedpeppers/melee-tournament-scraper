#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Normalize deck archetype names for a specific event's decklists and pairings
based on a provided mapping.

Environment:
- EVENT_DATA_DIR: path to the event folder under data/
- EVENT_NAME: event name (used to locate files)

Edits in place these files if present:
- <EVENT_DATA_DIR>/<EVENT_NAME> decklists.csv (column: deck_archetype)
- <EVENT_DATA_DIR>/<EVENT_NAME> pairings.csv (columns: PlayerDeck, OpponentDeck, WinningDeck)
"""

from __future__ import annotations
from pathlib import Path
import os
import sys
import pandas as pd


# Mapping as provided (old_name -> new_name)
DECKNAME_MAP = {
    "W-U-B-G Goryo's Vengeance": "Esper Goryo's",
    "W-U-R-G Domain Zoo": "Domain Zoo",
    "Mono-Red Storm": "Ruby Storm",
    "Izzet": "Izzet Affinity",
    "Colorless Tron": "Eldrazi Tron",
    "Izzet Aggro": "Izzet Prowess",
    "Jeskai Midrange": "Jeskai Blink",
    "Mono-Red Combo": "Ruby Storm",
    "W-U-R-G Aggro": "Domain Zoo",
    "W-U-B-G Control": "Esper Goryo's",
    "Simic Combo": "Simic Neoform",
    "Boros": "Boros Energy",
    "Jeskai": "Jeskai Blink",
    "Esper Midrange": "Esper Blink",
    "Izzet Murktide": "Izzet Prowess",
    "Gruul Eldrazi Ramp": "Eldrazi Ramp",
    "Gruul Eldrazi": "Eldrazi Aggro",
    "Jeskai Aggro": "Jeskai Blink",
    # Additional mappings provided later
    "Boros Aggro": "Boros Energy",
    "Boros Storm": "Ruby Storm",
    "Esper": "Esper Blink",
    "Colorless": "Eldrazi Tron",
    "Mono-Green Tron": "Eldrazi Tron",
    "W-U-R-G": "Domain Zoo",
    "W-U-R-G Midrange": "Domain Zoo",
}


def replace_and_count(series: pd.Series, mapping: dict[str, str]) -> tuple[pd.Series, int]:
    before = series.copy()
    after = series.replace(mapping)
    changed = (before != after) & ~(before.isna() & after.isna())
    return after, int(changed.sum())


def normalize_event() -> int:
    event_data_dir = os.getenv("EVENT_DATA_DIR")
    event_name = os.getenv("EVENT_NAME")
    if not event_data_dir or not event_name:
        print("ERROR: EVENT_DATA_DIR and EVENT_NAME must be set.", file=sys.stderr)
        return 1

    event_dir = Path(event_data_dir)
    decklists_path = event_dir / f"{event_name} decklists.csv"
    pairings_path = event_dir / f"{event_name} pairings.csv"

    any_updated = False

    if decklists_path.exists():
        print(f"Normalizing decklists: {decklists_path}")
        ddf = pd.read_csv(decklists_path)
        if 'deck_archetype' in ddf.columns:
            ddf['deck_archetype'], n = replace_and_count(ddf['deck_archetype'], DECKNAME_MAP)
            print(f"  deck_archetype changes: {n}")
            any_updated = any_updated or (n > 0)
        else:
            print("  WARNING: deck_archetype column not found; skipping decklists normalization")
        ddf.to_csv(decklists_path, index=False)
    else:
        print(f"Decklists not found: {decklists_path}")

    if pairings_path.exists():
        print(f"Normalizing pairings: {pairings_path}")
        pdf = pd.read_csv(pairings_path)
        for col in ['PlayerDeck', 'OpponentDeck', 'WinningDeck']:
            if col in pdf.columns:
                pdf[col], n = replace_and_count(pdf[col], DECKNAME_MAP)
                print(f"  {col} changes: {n}")
                any_updated = any_updated or (n > 0)
            else:
                print(f"  WARNING: {col} column not found; skipping")
        pdf.to_csv(pairings_path, index=False)
    else:
        print(f"Pairings not found: {pairings_path}")

    if any_updated:
        print("Normalization completed with changes.")
    else:
        print("Normalization completed; no changes were necessary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(normalize_event())
