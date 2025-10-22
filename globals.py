# -*- coding: utf-8 -*-
"""
@author: peterpiperpickedpeppers.

Description: Defines global config values shared across scripts.
"""

from utils.create_directory import create_tournament_folder
import os

# globals
class TournamentConfig:
    def __init__(self):
        self.tournamentID = None
        self.eventName = None
        self.basetournamentURL = "https://melee.gg/Tournament/View/"
        self.basedecklistURL = "https://melee.gg/Decklist/View/"
        self.tournamentURL = None
        self.decklistURL = None
        self.browser_instance = None
        self.data_folder = None
        self.results_folder = None
        self.matchups_folder = None
        self.archetypes_file = None
    
    def initialize(self, tournament_ID, event_name):
        """Initialize tournament identifiers and generate file paths."""
        self.tournamentID = tournament_ID
        self.eventName = event_name
        self.tournamentURL = f"{self.basetournamentURL}{tournament_ID}"
        self.decklistURL = self.basedecklistURL
        
        # create the tournament data folder using 'create_tournament_folder()'
        self.data_folder = create_tournament_folder(event_name)
        
        # define subfolder paths
        self.results_folder = os.path.join(self.data_folder, "results")
        self.matchups_folder = os.path.join(self.data_folder, "matchups")
        self.archetypes_file = os.path.join(self.data_folder, f"{event_name} archetypes.csv")
        
        # create results and matchups folders
        os.makedirs(self.results_folder, exist_ok=True)
        os.makedirs(self.matchups_folder, exist_ok=True)
        
    def reset(self):
        """Reset all values to None (useful for rerunning initialization)."""
        self.__init__()
    
# singleton instance of the config
CONFIG = TournamentConfig()
