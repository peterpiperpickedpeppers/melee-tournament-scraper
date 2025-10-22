# -*- coding: utf-8 -*-
"""
@author: peterpiperpickedpeppers
Description: Common data loading and saving utilities.
"""

import pandas as pd
import os
import re

def save_df(df, path):
    """Save a DataFrame to a CSV File"""
    df.to_csv(path, encoding="utf-8-sig", index=False)
    
def load_pairings(file_path):
    """Load pairings CSV into a DataFrame"""
    return pd.read_csv(file_path)

def get_unique_archetypes(df):
    """Return a list of unique archetypes from decklists columns."""
    return pd.unique(pd.concat([df['Decklist1'], df['Decklist2']]).dropna())

def filter_by_archetype(df, archetype):
    """Filter matches that contain the chosen archetype."""
    return df[df['Decklist1'].str.contains(archetype, na=False) | df['Decklist2'].str.contains(archetype, na=False)]

def create_sub_folder(base_folder, folder_name):
    """Create a sub folder if it doesn't exist."""
    subfolder_path = os.path.join(base_folder, folder_name)
    if not os.path.exists(subfolder_path):
        os.makedirs(subfolder_path)
    return subfolder_path

def clean_player_name(name):
    """Removes pronouns from player names on melee standings."""
    pronoun_pattern = re.compile(r"\s*\(?\b(?:he/him|she/her|they/them|he/they|she/they|they/she|they/he|other)\b\)?", re.IGNORECASE)
    return pronoun_pattern.sub("", name).strip()
