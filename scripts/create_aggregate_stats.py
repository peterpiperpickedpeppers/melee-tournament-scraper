#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Aggregate wins, losses, and draws for each archetype across all matchups."""

import os
import pandas as pd
from pathlib import Path

def create_aggregate_stats():
    # Get the event directory from environment
    event_data_dir = os.getenv('EVENT_DATA_DIR')
    if not event_data_dir:
        raise ValueError("EVENT_DATA_DIR environment variable not set")
    
    # Setup directories
    matchups_dir = Path(event_data_dir) / 'matchups'
    
    if not matchups_dir.exists():
        raise ValueError(f"Matchups directory not found: {matchups_dir}")
    
    # Collect aggregate stats for each archetype
    aggregate_rows = []
    
    for matchup_file in sorted(matchups_dir.glob('*matchups.csv')):
        # Extract archetype name from filename
        archetype = matchup_file.stem.replace(' matchups', '')
        
        # Read the matchup file
        df = pd.read_csv(matchup_file)
        
        # Sum wins, losses, draws across all opponent matchups
        total_wins = df['Wins'].sum()
        total_losses = df['Losses'].sum()
        total_draws = df['Draws'].sum()
        total_matches = df['Total_Matches'].sum()
        
        # Calculate overall winrate
        winrate = (total_wins / total_matches) * 100 if total_matches > 0 else 0
        
        aggregate_rows.append({
            'Archetype': archetype,
            'Wins': total_wins,
            'Losses': total_losses,
            'Draws': total_draws,
            'Total_Matches': total_matches,
            'Winrate': round(winrate, 1)
        })
    
    # Create DataFrame and sort by wins descending
    aggregate_df = pd.DataFrame(aggregate_rows)
    aggregate_df = aggregate_df.sort_values('Wins', ascending=False)
    
    # Write to CSV in the event root directory
    event_name = os.getenv('EVENT_NAME', 'event')
    output_file = Path(event_data_dir) / f'{event_name} aggregate stats.csv'
    aggregate_df.to_csv(output_file, index=False)
    
    print(f"Created aggregate stats file: {output_file}")
    print(f"Total archetypes: {len(aggregate_rows)}")
    
    return aggregate_df

if __name__ == '__main__':
    df = create_aggregate_stats()
    print("\nTop 10 archetypes by total wins:")
    print(df.head(10).to_string(index=False))
