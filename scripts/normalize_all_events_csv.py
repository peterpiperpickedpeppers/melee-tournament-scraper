#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Normalize archetype labels in the combined all-events pairings CSV.

Edits in-place by default:
- 'Azorius Control (Kaheera)' -> 'Azorius Control'
- Any case-insensitive 'roodscale' token -> 'Broodscale'

Usage:
    python -m scripts.normalize_all_events_csv [optional_path]
If optional_path is omitted, defaults to data/all_events/modern_rcs_all_pairings.csv
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd


def normalize_csv(csv_path: Path) -> None:
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    deck_cols = [c for c in df.columns if 'deck' in c.lower()]
    if not deck_cols:
        raise SystemExit("No deck columns found to normalize.")

    print(f"Normalizing columns: {deck_cols}")

    total_changes = 0
    kaheera_changes = 0
    broodscale_changes = 0

    for c in deck_cols:
        before = df[c].astype(str)
        # Normalize Kaheera control
        df[c] = before.str.replace('Azorius Control (Kaheera)', 'Azorius Control', regex=False)
        kaheera_changes += (before != df[c]).sum()

        # Fix any 'roodscale' token (case-insensitive) to 'Broodscale'
        before2 = df[c].astype(str)
        df[c] = before2.str.replace(r"\broodscale\b", "Broodscale", case=False, regex=True)
        broodscale_changes += (before2 != df[c]).sum()

    total_changes = kaheera_changes + broodscale_changes
    df.to_csv(csv_path, index=False)
    print(f"Wrote normalized CSV: {csv_path}")
    print(f"Kaheera label changes: {kaheera_changes}")
    print(f"Broodscale token fixes: {broodscale_changes}")
    print(f"Total changes: {total_changes}")


def main(argv: list[str]) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_path = repo_root / 'data' / 'all_events' / 'modern_rcs_all_pairings.csv'
    csv_path = Path(argv[1]) if len(argv) > 1 else default_path
    normalize_csv(csv_path)


if __name__ == '__main__':
    main(sys.argv)
