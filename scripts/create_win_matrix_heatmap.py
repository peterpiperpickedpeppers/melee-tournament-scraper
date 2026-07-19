#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Create a heatmap visualization of the win matrix with winrates."""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


HEATMAP_STYLES = {
    # Softer default palette and text settings for easier readability.
    'soft': {
        'cmap': 'crest',
        'font_family': ['Segoe UI', 'Arial', 'sans-serif'],
        'annot_fontsize': 12,
        'title_fontsize': 16,
        'tick_fontweight': 'normal',
        'linewidths': 0.3,
        'linecolor': '#f0f0f0',
        'clip_percentiles': (5, 95),
    },
    'print': {
        'cmap': 'YlGnBu',
        'font_family': ['Calibri', 'Arial', 'sans-serif'],
        'annot_fontsize': 12,
        'title_fontsize': 16,
        'tick_fontweight': 'normal',
        'linewidths': 0.4,
        'linecolor': '#e6e6e6',
        'clip_percentiles': None,
    },
    'colorblind': {
        'cmap': 'cividis',
        'font_family': ['Verdana', 'Arial', 'sans-serif'],
        'annot_fontsize': 12,
        'title_fontsize': 16,
        'tick_fontweight': 'normal',
        'linewidths': 0.3,
        'linecolor': '#ececec',
        'clip_percentiles': (5, 95),
    },
}


def _resolve_style(style_name):
    style_key = (style_name or 'soft').strip().lower()
    if style_key not in HEATMAP_STYLES:
        valid = ', '.join(sorted(HEATMAP_STYLES.keys()))
        print(f"Unknown HEATMAP_STYLE '{style_name}', using 'soft'. Valid styles: {valid}")
        style_key = 'soft'
    return style_key, HEATMAP_STYLES[style_key]


def _resolve_annot_fontsize(default_size):
    size_override = os.getenv('HEATMAP_ANNOT_FONTSIZE', '').strip()
    if not size_override:
        return default_size

    try:
        parsed = float(size_override)
        if parsed <= 0:
            raise ValueError
        return parsed
    except ValueError:
        print(f"Invalid HEATMAP_ANNOT_FONTSIZE '{size_override}', using {default_size}.")
        return default_size


def _apply_annotation_colors(ax, mode='auto'):
    mode_key = (mode or 'auto').strip().lower()
    if mode_key not in ('auto', 'dark', 'light'):
        print(f"Invalid HEATMAP_TEXT_MODE '{mode}', using 'auto'.")
        mode_key = 'auto'

    if mode_key == 'dark':
        for text in ax.texts:
            text.set_color('#1f1f1f')
        return

    if mode_key == 'light':
        for text in ax.texts:
            text.set_color('#f7f7f7')
        return

    mesh = ax.collections[0] if ax.collections else None
    if mesh is None:
        return

    facecolors = mesh.get_facecolors()
    for text, rgba in zip(ax.texts, facecolors):
        r, g, b, _ = rgba
        luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
        text.set_color('#f7f7f7' if luminance < 0.50 else '#1f1f1f')


def create_win_matrix_heatmap(top_n=15, show=False, style_name='soft'):
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
    
    style_key, style = _resolve_style(style_name)
    cmap_override = os.getenv('HEATMAP_CMAP', '').strip()
    text_mode = os.getenv('HEATMAP_TEXT_MODE', 'auto')
    cmap_to_use = style['cmap']
    if cmap_override:
        if cmap_override in plt.colormaps():
            cmap_to_use = cmap_override
        else:
            print(f"Unknown HEATMAP_CMAP '{cmap_override}', using style colormap '{style['cmap']}'.")
    print(f"Creating heatmap for top {top_n} archetypes (style='{style_key}', cmap='{cmap_to_use}')...")
    
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

    sns.set_theme(style='white')
    plt.rcParams['font.family'] = style['font_family']

    clip_percentiles = style['clip_percentiles']
    if clip_percentiles:
        finite_values = winrate_df.to_numpy(dtype=float)
        finite_values = finite_values[~np.isnan(finite_values)]
        if finite_values.size > 0:
            vmin, vmax = np.percentile(finite_values, clip_percentiles)
        else:
            vmin, vmax = 0, 100
    else:
        vmin, vmax = 0, 100

    annot_fontsize = _resolve_annot_fontsize(style['annot_fontsize'])

    # Keep the midpoint at 50% and use style-specific palette/line settings.
    ax = sns.heatmap(winrate_df,
                     annot=annotation_df,
                     fmt='',
                     cmap=cmap_to_use,
                     center=50,
                     vmin=vmin,
                     vmax=vmax,
                     cbar=False,  # Remove the colorbar legend
                     linewidths=style['linewidths'],
                     linecolor=style['linecolor'],
                     square=False,
                     annot_kws={'fontsize': annot_fontsize, 'ha': 'center', 'va': 'center'},
                     xticklabels=True,
                     yticklabels=True)

    _apply_annotation_colors(ax, mode=text_mode)
    
    # Move x-axis labels to top
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    
    plt.title(f'Win Matrix - Top {top_n} Archetypes',
              fontsize=style['title_fontsize'], fontweight='bold', pad=20, y=1.08)
    
    # Rotate labels for better readability
    plt.xticks(rotation=45, ha='left', fontweight=style['tick_fontweight'])
    plt.yticks(rotation=0, fontweight=style['tick_fontweight'])
    
    plt.tight_layout()
    
    # Save the figure
    event_name = os.getenv('EVENT_NAME', 'event')
    event_name = event_name.strip() if isinstance(event_name, str) else event_name
    output_suffix = ''
    if cmap_override and cmap_to_use == cmap_override:
        output_suffix = f' {cmap_to_use}'
    output_file = Path(event_data_dir) / f'{event_name} win matrix heatmap top{top_n}{output_suffix}.png'
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
    _style = os.getenv('HEATMAP_STYLE', 'soft')
    winrate_df, annotation_df = create_win_matrix_heatmap(top_n=15, show=_show, style_name=_style)
    print("\nWinrate matrix:")
    print(winrate_df.to_string())
