#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Verify head-to-head records between two archetypes.

Usage:
    python scripts/verify_matchup.py --deck-a "Azorius Blink" --deck-b "Esper Goryo's"

This reads per-archetype results and/or matchup files under EVENT_DATA_DIR and
prints W/L/D counts from both perspectives, asserting symmetry.
"""

import argparse
import os
from pathlib import Path
import sys
import pandas as pd


def load_matchup_row(matchups_file: Path, opponent: str) -> dict | None:
    df = pd.read_csv(matchups_file)
    row = df[df['Opponent_Archetype'] == opponent]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        'wins': int(r['Wins']),
        'losses': int(r['Losses']),
        'draws': int(r['Draws']),
        'total': int(r['Total_Matches']),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify symmetric head-to-head matchup records.")
    ap.add_argument('--deck-a', required=True, help='First archetype name (as in filenames)')
    ap.add_argument('--deck-b', required=True, help='Second archetype name (as in filenames)')
    ap.add_argument('--event-dir', default=os.getenv('EVENT_DATA_DIR'), help='Event data directory (defaults to EVENT_DATA_DIR)')
    args = ap.parse_args()

    if not args.event_dir:
        print('ERROR: EVENT_DATA_DIR not set and --event-dir not provided', file=sys.stderr)
        return 2

    event_dir = Path(args.event_dir)
    matchups_dir = event_dir / 'matchups'

    file_a = matchups_dir / f"{args.deck_a} matchups.csv"
    file_b = matchups_dir / f"{args.deck_b} matchups.csv"

    if not file_a.exists() or not file_b.exists():
        print(f"ERROR: Missing matchup files: {file_a if not file_a.exists() else ''} {file_b if not file_b.exists() else ''}", file=sys.stderr)
        return 2

    a_vs_b = load_matchup_row(file_a, args.deck_b)
    b_vs_a = load_matchup_row(file_b, args.deck_a)

    if a_vs_b is None or b_vs_a is None:
        print('ERROR: Could not find matchup rows in one or both files.', file=sys.stderr)
        return 2

    print(f"{args.deck_a} vs {args.deck_b}:")
    print(f"  A perspective -> W:{a_vs_b['wins']} L:{a_vs_b['losses']} D:{a_vs_b['draws']} (T:{a_vs_b['total']})")
    print(f"  B perspective -> W:{b_vs_a['wins']} L:{b_vs_a['losses']} D:{b_vs_a['draws']} (T:{b_vs_a['total']})")

    ok = True
    if a_vs_b['wins'] != b_vs_a['losses']:
        print('Mismatch: A wins != B losses', file=sys.stderr)
        ok = False
    if a_vs_b['losses'] != b_vs_a['wins']:
        print('Mismatch: A losses != B wins', file=sys.stderr)
        ok = False
    if a_vs_b['draws'] != b_vs_a['draws']:
        print('Mismatch: draws differ', file=sys.stderr)
        ok = False
    if a_vs_b['total'] != (a_vs_b['wins'] + a_vs_b['losses'] + a_vs_b['draws']):
        print('A total does not sum to W+L+D', file=sys.stderr)
        ok = False
    if b_vs_a['total'] != (b_vs_a['wins'] + b_vs_a['losses'] + b_vs_a['draws']):
        print('B total does not sum to W+L+D', file=sys.stderr)
        ok = False

    print('\nSymmetry check:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
