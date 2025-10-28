#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Combine decklist CSVs from multiple Regional Championship events into a single file.

Reads all '*decklists.csv' files from RC event folders under data/ and combines
them into a single CSV with an Event column added to track the source event.

Usage:
    python -m scripts.combine_decklists
    
Output: data/all_events/modern_rcs_all_decklists.csv
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import re


def extract_event_name(path: Path) -> str:
    """Extract a clean event name from the file path."""
    # Get the parent directory name (e.g., "RC Houston 2025")
    parent = path.parent.name
    if parent.startswith('RC '):
        return parent
    # Fallback: try to extract from filename
    match = re.search(r'(RC [^_]+)', path.stem)
    if match:
        return match.group(1)
    return parent


def combine_decklists() -> None:
    """Combine all RC decklist CSVs into a single file."""
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / 'data'
    
    # Find all RC event directories
    rc_dirs = sorted([d for d in data_dir.iterdir() 
                     if d.is_dir() and d.name.startswith('RC ')])
    
    if not rc_dirs:
        raise SystemExit(f"No RC event directories found in {data_dir}")
    
    print(f"Found {len(rc_dirs)} RC event directories")
    
    # Collect all decklist files
    decklist_files = []
    for rc_dir in rc_dirs:
        decklists = list(rc_dir.glob('*decklists.csv'))
        if decklists:
            decklist_files.append(decklists[0])  # Take the first match
            print(f"  {rc_dir.name}: {decklists[0].name}")
    
    if not decklist_files:
        raise SystemExit("No decklist CSV files found in RC directories")
    
    print(f"\nCombining {len(decklist_files)} decklist files...")
    
    # Read and combine all files
    combined_dfs = []
    for file_path in decklist_files:
        df = pd.read_csv(file_path)
        event_name = extract_event_name(file_path)
        df['Event'] = event_name
        combined_dfs.append(df)
        print(f"  Loaded {len(df):,} rows from {event_name}")
    
    # Concatenate all dataframes
    combined = pd.concat(combined_dfs, ignore_index=True)
    
    # Reorder columns to put Event first (after player)
    cols = combined.columns.tolist()
    if 'Event' in cols and 'player' in cols:
        cols.remove('Event')
        player_idx = cols.index('player')
        cols.insert(player_idx + 1, 'Event')
        combined = combined[cols]
    
    # Write output
    output_dir = data_dir / 'all_events'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'modern_rcs_all_decklists.csv'
    
    combined.to_csv(output_path, index=False)
    print(f"\nWrote combined decklists with {len(combined):,} rows from {len(decklist_files)} files.")
    print(f"Output: {output_path}")
    
    # Print summary stats
    print(f"\nSummary:")
    print(f"  Total cards across all decklists: {len(combined):,}")
    print(f"  Unique players: {combined['player'].nunique():,}")
    print(f"  Unique archetypes: {combined['deck_archetype'].nunique():,}")
    print(f"  Events: {combined['Event'].nunique()}")
    print("\nCards per event:")
    print(combined.groupby('Event').size().to_string())


if __name__ == '__main__':
    combine_decklists()
