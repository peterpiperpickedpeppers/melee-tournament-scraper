#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Create a win matrix showing head-to-head records between top archetypes."""

import os
import pandas as pd
from pathlib import Path

def create_win_matrix(top_n=15):
    # Get the event directory from environment
    event_data_dir = os.getenv('EVENT_DATA_DIR')
    event_data_dir = event_data_dir.strip() if isinstance(event_data_dir, str) else event_data_dir
    if not event_data_dir:
        raise ValueError("EVENT_DATA_DIR environment variable not set")
    
    # Setup directories
    matchups_dir = Path(event_data_dir) / 'matchups'
    
    if not matchups_dir.exists():
        raise ValueError(f"Matchups directory not found: {matchups_dir}")
    
    # First, determine the top N archetypes by total matches
    archetype_totals = []
    for matchup_file in matchups_dir.glob('*matchups.csv'):
        archetype = matchup_file.stem.replace(' matchups', '')
        df = pd.read_csv(matchup_file)
        total_matches = df['Total_Matches'].sum()
        archetype_totals.append({'Archetype': archetype, 'Total_Matches': total_matches})
    
    totals_df = pd.DataFrame(archetype_totals).sort_values('Total_Matches', ascending=False)
    top_archetypes = totals_df.head(top_n)['Archetype'].tolist()
    
    print(f"Top {top_n} archetypes by total matches:")
    for i, row in totals_df.head(top_n).iterrows():
        print(f"  {row['Archetype']}: {row['Total_Matches']} matches")
    print()
    
    # Build the win matrix
    # Matrix will show: row archetype's wins against column archetype
    matrix_data = {}
    
    for archetype in top_archetypes:
        matchup_file = matchups_dir / f'{archetype} matchups.csv'
        df = pd.read_csv(matchup_file)
        
        # Create a row for this archetype
        row = {}
        for opponent in top_archetypes:
            if archetype == opponent:
                # Mirror matches are excluded, so put a dash
                row[opponent] = '-'
            else:
                # Find the matchup data
                matchup = df[df['Opponent_Archetype'] == opponent]
                if len(matchup) > 0:
                    wins = matchup['Wins'].values[0]
                    losses = matchup['Losses'].values[0]
                    draws = matchup['Draws'].values[0]
                    # Format as "W-L-D"
                    row[opponent] = f"{wins}-{losses}-{draws}"
                else:
                    row[opponent] = "0-0-0"
        
        matrix_data[archetype] = row
    
    # Create DataFrame
    matrix_df = pd.DataFrame(matrix_data).T
    matrix_df.index.name = 'Archetype'
    
    # Write to CSV
    event_name = os.getenv('EVENT_NAME', 'event')
    event_name = event_name.strip() if isinstance(event_name, str) else event_name
    output_file = Path(event_data_dir) / f'{event_name} win matrix top{top_n}.csv'
    matrix_df.to_csv(output_file)
    
    print(f"Created win matrix: {output_file}")
    print(f"\nMatrix preview (row vs column):")
    print(matrix_df.to_string())
    
    return matrix_df

if __name__ == '__main__':
    create_win_matrix(top_n=15)
