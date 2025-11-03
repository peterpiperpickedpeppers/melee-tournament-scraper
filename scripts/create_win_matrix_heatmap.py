#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Create a heatmap visualization of the win matrix with winrates."""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path

def create_win_matrix_heatmap(top_n=15, show=False):
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
    
    print(f"Creating heatmap for top {top_n} archetypes...")
    
    # Get overall winrates for each archetype
    overall_winrates = {}
    overall_stats = {}
    for archetype in top_archetypes:
        matchup_file = matchups_dir / f'{archetype} matchups.csv'
        df = pd.read_csv(matchup_file)
        total_wins = df['Wins'].sum()
        total_losses = df['Losses'].sum()
        total_draws = df['Draws'].sum()
        total_matches = total_wins + total_losses + total_draws
        winrate = (total_wins / total_matches * 100) if total_matches > 0 else 0
        overall_winrates[archetype] = winrate
        overall_stats[archetype] = {
            'wins': int(total_wins),
            'losses': int(total_losses),
            'draws': int(total_draws),
            'winrate': winrate
        }
    
    # Build the win matrix with annotations and numeric winrates
    winrate_matrix = []
    annotation_matrix = []
    
    for archetype in top_archetypes:
        matchup_file = matchups_dir / f'{archetype} matchups.csv'
        df = pd.read_csv(matchup_file)
        
        winrate_row = []
        annotation_row = []
        
        # Add overall winrate as the first column
        overall_wr = overall_winrates[archetype]
        stats = overall_stats[archetype]
        winrate_row.append(overall_wr)
        annotation_row.append(f"{stats['wins']}-{stats['losses']}-{stats['draws']}\n({overall_wr:.1f}%)")
        
        for opponent in top_archetypes:
            if archetype == opponent:
                # Mirror matches - set to NaN for visual distinction
                winrate_row.append(np.nan)
                annotation_row.append('-')
            else:
                # Find the matchup data
                matchup = df[df['Opponent_Archetype'] == opponent]
                if len(matchup) > 0:
                    wins = int(matchup['Wins'].values[0])
                    losses = int(matchup['Losses'].values[0])
                    draws = int(matchup['Draws'].values[0])
                    total = wins + losses + draws
                    winrate = (wins / total * 100) if total > 0 else 0
                    
                    # Create annotation: "W-L-D (WR%)"
                    annotation_row.append(f"{wins}-{losses}-{draws}\n({winrate:.1f}%)")
                    winrate_row.append(winrate)
                else:
                    annotation_row.append("0-0-0\n(0.0%)")
                    winrate_row.append(0)
        
        winrate_matrix.append(winrate_row)
        annotation_matrix.append(annotation_row)
    
    # Create DataFrames with "Overall WR" as first column
    columns = ['Overall WR'] + top_archetypes
    winrate_df = pd.DataFrame(winrate_matrix, index=top_archetypes, columns=columns)
    annotation_df = pd.DataFrame(annotation_matrix, index=top_archetypes, columns=columns)
    
    # Create the heatmap
    fig = plt.figure(figsize=(18, 12))
    
    # Set font - use Arial or Segoe UI (common on Windows)
    try:
        plt.rcParams['font.family'] = 'Arial'
    except Exception:
        plt.rcParams['font.family'] = 'sans-serif'
    
    # Use a diverging colormap centered at 50%
    sns.heatmap(winrate_df, 
                annot=annotation_df, 
                fmt='',
                cmap='RdYlGn',
                center=50,
                vmin=0,
                vmax=100,
                cbar=False,  # Remove the colorbar legend
                linewidths=0.5,
                linecolor='gray',
                square=False,
                annot_kws={'fontsize': 14, 'ha': 'center', 'va': 'center'},
                xticklabels=True,
                yticklabels=True)
    
    # Move x-axis labels to top
    ax = plt.gca()
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    
    plt.title(f'Win Matrix - Top {top_n} Archetypes',
              fontsize=16, fontweight='bold', pad=20, y=1.08)
    
    # Rotate labels for better readability and make them bold
    plt.xticks(rotation=45, ha='left', fontweight='bold')
    plt.yticks(rotation=0, fontweight='bold')
    
    plt.tight_layout()
    
    # Save the figure
    event_name = os.getenv('EVENT_NAME', 'event')
    event_name = event_name.strip() if isinstance(event_name, str) else event_name
    output_file = Path(event_data_dir) / f'{event_name} win matrix heatmap top{top_n}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved heatmap to: {output_file}")
    
    if show:
        plt.show()
    else:
        plt.close(fig)
    
    return winrate_df, annotation_df

if __name__ == '__main__':
    # Allow opt-in display via env SHOW_PLOT=1
    _show = os.getenv('SHOW_PLOT', '0') in ('1', 'true', 'True')
    winrate_df, annotation_df = create_win_matrix_heatmap(top_n=15, show=_show)
    print("\nWinrate matrix:")
    print(winrate_df.to_string())
