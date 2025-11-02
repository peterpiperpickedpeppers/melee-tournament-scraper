#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate metagame breakdown CSV from decklists.

Reads the decklists CSV for the current event and produces a metagame breakdown
showing the number of pilots for each deck archetype, sorted by popularity.

Outputs to: <EVENT_DATA_DIR>/<EVENT_NAME> metagame breakdown.csv

Environment variables required:
- EVENT_DATA_DIR: path to the event data folder
- EVENT_NAME: name of the event (used in output filename)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
import pandas as pd


def main() -> int:
    event_data_dir = os.getenv("EVENT_DATA_DIR")
    event_name = os.getenv("EVENT_NAME")

    if not event_data_dir or not event_name:
        print("ERROR: EVENT_DATA_DIR and EVENT_NAME environment variables must be set.", file=sys.stderr)
        return 1

    event_dir = Path(event_data_dir)
    decklists_path = event_dir / f"{event_name} decklists.csv"
    output_path = event_dir / f"{event_name} metagame breakdown.csv"

    if not decklists_path.exists():
        print(f"ERROR: Decklists file not found: {decklists_path}", file=sys.stderr)
        return 1

    print(f"Loading decklists from: {decklists_path}")
    df = pd.read_csv(decklists_path)

    # Count unique players per deck archetype
    metagame = df.groupby('deck_archetype', as_index=False).agg(
        Pilots=('player', 'nunique')
    ).sort_values('Pilots', ascending=False)

    # Add percentage column
    total_pilots = metagame['Pilots'].sum()
    metagame['Percentage'] = (metagame['Pilots'] / total_pilots * 100).round(2)

    # Rename deck_archetype column for clarity
    metagame = metagame.rename(columns={'deck_archetype': 'Deck_Archetype'})

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metagame.to_csv(output_path, index=False)

    print(f"\nMetagame Breakdown for {event_name}")
    print("=" * 70)
    print(f"Total Pilots: {total_pilots}")
    print(f"Total Archetypes: {len(metagame)}")
    print("\nTop 10 Decks:")
    print(metagame.head(10).to_string(index=False))
    print(f"\nWrote metagame breakdown to: {output_path}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
