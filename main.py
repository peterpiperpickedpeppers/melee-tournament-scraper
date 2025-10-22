# -*- coding: utf-8 -*-
"""
@author: peterpiperpickedpeppers.

Description: Runs the tournament scraping workflow.
"""

from globals import CONFIG
from utils.browser_manager import BrowserManager
from scripts.scrape_standings import run_standings_scraper
from scripts.scrape_pairings import run_pairings_scraper
from scripts.scrape_decklists import run_decklists_scraper
from scripts.archetypes_results import create_archetypes_results
from scripts.archetypes_matchups import create_archetypes_matchups
from scripts.archetypes_winrates import create_archetype_winrates
# from scripts.pro_tour_scrape_decklists import run_decklists_scraper

def run_tournament_scraper():
    """Runs the tournament scraper scripts in order after input from user."""
    
    # Get user input for tournament ID and event name
    tournament_ID = input("Enter the tournament ID: ").strip()
    event_name = input("Enter the Event Name: ").strip()

    # Call CONFIG.initialize() to set all paths correctly
    CONFIG.initialize(tournament_ID, event_name)

    print(CONFIG.tournamentURL)

    print(f"Initialized tournament scraping for: {CONFIG.eventName}")

    # Initialize browser and open URL
    browser = BrowserManager(CONFIG.tournamentURL)
    CONFIG.browser_instance = browser.open_browser()

    input()
    # Run scripts sequentially
    
    try:
        # scripts that use the browser
        run_standings_scraper()
        run_pairings_scraper()
        run_decklists_scraper()
    
    finally:
        # close browser
        browser.close_browser()
        CONFIG.browser_instance = None
    
    # scripts that don't need the browser
    create_archetypes_results()
    create_archetypes_matchups()
    create_archetype_winrates()
    
    print("Scraping complete!")
    
if __name__ == "__main__":
    run_tournament_scraper()





