#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers


import os
import re
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone


def _sanitize_filename(s: str) -> str:
    # replace problematic filesystem characters
    return re.sub(r'[<>:"/\\|?*]', '_', s).strip()


def create_archetypes_results():
    """Filter pairings csv to create archetype-specific results files.

    Behavior:
    - Detect event folder using EVENT_DATA_DIR or data/<EVENT_NAME>.
    - Find the most-recent pairings CSV (prefer filenames containing 'pairings').
    - Extract archetypes from the two deck columns (any column with 'deck' in its name).
    - For each unique archetype, write a CSV with all rows where either side's deck equals that archetype.
    - Save outputs to: data/<event>/results/{sanitized_archetype} results.csv
    """

    repo_root = Path(__file__).resolve().parents[1]
    # event directory override (set by main.py) or default to data/<EVENT_NAME> or data/event
    event_name_env = os.environ.get("EVENT_NAME") or "event"
    event_name_env = event_name_env.strip() if isinstance(event_name_env, str) else event_name_env
    default_event_dir = repo_root / "data" / event_name_env
    event_data_dir_env = os.environ.get("EVENT_DATA_DIR")
    if isinstance(event_data_dir_env, str):
        event_data_dir_env = event_data_dir_env.strip()
    event_dir = Path(event_data_dir_env or default_event_dir)

    if not event_dir.exists():
        raise SystemExit(f"Event data directory not found: {event_dir}")

    # find pairings CSV: prefer files with 'pairings' in name, else any csv
    # Prefer true pairings files (exclude derived "unique archetypes" lists)
    pairings_candidates = [p for p in event_dir.glob("*pairings*.csv") if "unique archetypes" not in p.name.lower()]
    pairings_candidates = sorted(pairings_candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    pairings_path = None
    if pairings_candidates:
        pairings_path = pairings_candidates[0]
    else:
        other_csvs = sorted(event_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        # prefer files that include 'pairings' in the header name; fallback to first CSV
        pairings_path = other_csvs[0] if other_csvs else None

    if pairings_path is None:
        raise SystemExit(f"No CSV files found in event dir: {event_dir}")

    print(f"Loading pairings from: {pairings_path}")
    df = pd.read_csv(pairings_path)

    # Filter out byes and incomplete matches: remove rows with ResultString == '0-0-3' or Outcome == 'Bye'
    initial_rows = len(df)
    if "ResultString" in df.columns:
        # Remove rows where ResultString contains '0-0-3' (e.g. '0-0-3 Draw')
        df = df[~df["ResultString"].fillna("").astype(str).str.contains(r"0-0-3", regex=True, na=False)]
    if "Outcome" in df.columns:
        df = df[~df["Outcome"].fillna("").astype(str).str.strip().str.lower().eq("bye")]
    filtered_rows = initial_rows - len(df)
    if filtered_rows:
        print(f"Filtered out {filtered_rows} rows with ResultString='0-0-3' or Outcome='Bye'")

    # try to locate the two deck columns automatically
    deck_cols = [c for c in df.columns if "deck" in c.lower()]
    if len(deck_cols) >= 2:
        player_col, opp_col = deck_cols[0], deck_cols[1]
    elif len(deck_cols) == 1:
        player_col = deck_cols[0]
        # attempt to find an opponent column explicitly
        opp_candidates = [c for c in df.columns if "opponent" in c.lower() and "deck" in c.lower()]
        opp_col = opp_candidates[0] if opp_candidates else player_col
    else:
        raise SystemExit("Could not find deck columns in pairings CSV (expecting columns with 'deck' in their name).")

    print(f"Using deck columns: player='{player_col}' opponent='{opp_col}'")

    # gather unique archetypes (deck strings) from both columns
    p_vals = df[player_col].fillna("").astype(str).str.strip()
    o_vals = df[opp_col].fillna("").astype(str).str.strip()
    combined = pd.concat([p_vals, o_vals], ignore_index=True)
    archetypes = sorted([v for v in pd.unique(combined) if v])

    print(f"Found {len(archetypes)} unique archetypes")

    results_dir = event_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)


    written = 0
    for archetype in archetypes:
        # filter rows where either side matches the archetype exactly
        mask_player = (p_vals == archetype)
        mask_opp = (o_vals == archetype)
        rows_player = df[mask_player].copy()
        rows_opp = df[mask_opp].copy()

        # For rows where archetype is the opponent, swap columns to normalize perspective
        if not rows_opp.empty:
            # Store original WinningDeck values before swapping columns
            original_winning_deck = rows_opp['WinningDeck'].copy() if 'WinningDeck' in rows_opp.columns else None
            original_player_deck = rows_opp[player_col].copy()
            original_opp_deck = rows_opp[opp_col].copy()
            
            # Swap player/opponent columns
            rows_opp[[player_col, opp_col]] = rows_opp[[opp_col, player_col]]
            # Swap player/opponent names if present
            if 'Player' in rows_opp.columns and 'Opponent' in rows_opp.columns:
                rows_opp[['Player', 'Opponent']] = rows_opp[['Opponent', 'Player']]
            # Adjust Outcome, WinningDeck, ResultString
            # For WinningDeck: keep the actual winning deck name unchanged
            # Just need to make sure it matches the new column positions
            if 'WinningDeck' in rows_opp.columns and original_winning_deck is not None:
                # The WinningDeck should remain the same deck name, we don't swap it
                # We just need to ensure it's still correct after column swap
                # If original WinningDeck was the original player (now opponent), it stays as-is
                # If original WinningDeck was the original opponent (now player), it stays as-is
                # The WinningDeck column already has the correct deck name, no need to change it
                rows_opp['WinningDeck'] = original_winning_deck
            # For Outcome: swap 'won' and 'lost' only if not a draw
            if 'Outcome' in rows_opp.columns:
                def swap_outcome(row):
                    val = str(row['Outcome'])
                    if 'draw' in val.lower():
                        return val
                    if 'won' in val.lower():
                        return val.lower().replace('won', 'lost').replace('Won', 'Lost')
                    if 'lost' in val.lower():
                        return val.lower().replace('lost', 'won').replace('Lost', 'Won')
                    return val
                rows_opp['Outcome'] = rows_opp.apply(swap_outcome, axis=1)
            # ResultString: leave as-is for now

        # Combine and sort
        combined_df = pd.concat([rows_player, rows_opp], ignore_index=True)
        if combined_df.empty:
            continue
        safe_name = _sanitize_filename(archetype) or "unknown"
        out_path = results_dir / f"{safe_name} results.csv"
        combined_df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Wrote {len(combined_df)} rows to {out_path}")
        written += 1

    # Use timezone-aware UTC timestamp to avoid deprecation warnings
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    print(f"{now} - Completed archetype filtering. Wrote {written} files to {results_dir}")


if __name__ == "__main__":
    create_archetypes_results()
    