#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""For each file in data/<event>/results/, create a file in data/<event>/matchups/ that shows winrates for that archetype vs each other archetype."""

import os
import pandas as pd
from pathlib import Path

def get_unique_archetypes(results_dir):
    """Get list of unique archetypes from results directory."""
    archetypes = []
    for file in os.listdir(results_dir):
        if file.endswith('results.csv'):
            archetype = file.replace(' results.csv', '')
            archetypes.append(archetype)
    return sorted(archetypes)

def process_archetype_results(archetype, results_dir):
    """Process results for a single archetype and compute matchup stats."""
    # Read the results file
    results_file = Path(results_dir) / f"{archetype} results.csv"
    df = pd.read_csv(results_file)
    
    # Initialize matchup tracking
    matchups = {}
    
    # Process each row to tally wins/losses/draws per opponent archetype
    player_col = 'PlayerDeck'
    opp_col = 'OpponentDeck'
    for _, row in df.iterrows():
        opponent_archetype = row[opp_col]
        result_string = str(row['ResultString'])
        outcome = str(row['Outcome'])
        
        # Skip if opponent archetype is the same (mirror match)
        if opponent_archetype == archetype:
            continue
        # Initialize matchup stats if not seen before
        if opponent_archetype not in matchups:
            matchups[opponent_archetype] = {'wins': 0, 'losses': 0, 'draws': 0}
        # Check for draws (look for "Draw" in outcome or result string, but not "0-0-3")
        if ('Draw' in outcome or 'Draw' in result_string) and '0-0-3' not in result_string:
            matchups[opponent_archetype]['draws'] += 1
        elif row['WinningDeck'] == row[player_col]:
            matchups[opponent_archetype]['wins'] += 1
        elif row['WinningDeck'] == row[opp_col]:
            matchups[opponent_archetype]['losses'] += 1
    
    # Convert matchups to DataFrame with win rates
    # Create DataFrame columns first
    columns = ['Opponent_Archetype', 'Wins', 'Losses', 'Draws', 'Total_Matches', 'Winrate']
    rows = []
    
    for opp_archetype, stats in matchups.items():
        total_matches = stats['wins'] + stats['losses'] + stats['draws']
        # Winrate: wins / (wins + losses + draws)
        winrate = (stats['wins'] / total_matches) * 100 if total_matches > 0 else 0
        rows.append([
            opp_archetype,
            stats['wins'],
            stats['losses'],
            stats['draws'],
            total_matches,
            round(winrate, 1)
        ])
    
    # Create DataFrame with explicit column names
    return pd.DataFrame(rows, columns=columns)
    
    return pd.DataFrame(rows)

def create_matchups_files():
    # Get the event directory from environment
    event_data_dir = os.getenv('EVENT_DATA_DIR')
    if not event_data_dir:
        raise ValueError("EVENT_DATA_DIR environment variable not set")
    
    # Setup directories
    results_dir = Path(event_data_dir) / 'results'
    matchups_dir = Path(event_data_dir) / 'matchups'
    matchups_dir.mkdir(exist_ok=True)
    
    # Get list of unique archetypes
    archetypes = get_unique_archetypes(results_dir)
    
    # Process each archetype
    for archetype in archetypes:
        # Calculate matchup stats
        matchup_df = process_archetype_results(archetype, results_dir)
        
        # Sort by number of matches played and winrate
        matchup_df = matchup_df.sort_values(
            ['Total_Matches', 'Winrate'],
            ascending=[False, False]
        )
        
        # Write matchup results to CSV
        output_file = matchups_dir / f"{archetype} matchups.csv"
        matchup_df.to_csv(output_file, index=False)
        print(f"Created matchup file for {archetype}")

if __name__ == "__main__":
    create_matchups_files()