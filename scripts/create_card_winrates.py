#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Create per-card, per-copy winrate CSVs for every archetype.

Reads the event decklists CSV, computes winrates by copy count for each
unique deck_archetype (including pilots who played 0 copies of a card),
and writes outputs to data/<EVENT_NAME>/card_winrates/.

Requires: EVENT_DATA_DIR and EVENT_NAME in the environment (set by main.py),
and an existing decklists CSV named "<EVENT_NAME> decklists.csv" in EVENT_DATA_DIR.
"""

import os
import sys
from pathlib import Path
import pandas as pd

# Ensure repository root is on sys.path for local imports when executed directly
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.card_winrates_per_archetype import archetype_card_copy_winrates


def _sanitize_filename(name: str) -> str:
    import re
    return re.sub(r'[<>:"/\\|?*]', '_', str(name))


def create_all_card_winrates(min_pilots: int = 0, max_copies_cap: int | None = 4) -> list[Path]:
    event_dir = os.getenv('EVENT_DATA_DIR')
    event_name = os.getenv('EVENT_NAME', 'event')
    event_dir = event_dir.strip() if event_dir else event_dir
    event_name = event_name.strip() if event_name else event_name
    if not event_dir:
        raise ValueError('EVENT_DATA_DIR environment variable not set')

    event_path = Path(event_dir)
    decklists_csv = event_path / f"{event_name} decklists.csv"
    if not decklists_csv.exists():
        raise FileNotFoundError(f"Decklists file not found: {decklists_csv}")

    out_dir = event_path / 'card_winrates'
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(decklists_csv)
    # Ensure expected columns present for the helper
    # helper will rename: player->pilot, card_name->card, qty->Copies, zone->loc, wins/losses

    # Drop rows with missing archetype
    df = df.dropna(subset=['deck_archetype']).copy()

    archetypes = sorted(df['deck_archetype'].dropna().unique().tolist())
    print(f"Found {len(archetypes)} unique archetypes in decklists")

    written_files: list[Path] = []
    for archetype in archetypes:
        try:
            tbl = archetype_card_copy_winrates(
                df,
                archetype=archetype,
                loc=None,
                min_pilots=min_pilots,
                max_copies_cap=max_copies_cap,
            )
        except Exception as e:
            print(f"Error computing card winrates for {archetype}: {e}")
            continue

        safe_name = _sanitize_filename(archetype)
        out_csv = out_dir / f"{safe_name} per card per copy winrates.csv"
        tbl.to_csv(out_csv, index=False, encoding='utf-8')
        written_files.append(out_csv)
        print(f"Wrote {len(tbl)} rows -> {out_csv}")

    print(f"Completed card winrates for {len(written_files)}/{len(archetypes)} archetypes.")
    return written_files


if __name__ == '__main__':
    create_all_card_winrates()
