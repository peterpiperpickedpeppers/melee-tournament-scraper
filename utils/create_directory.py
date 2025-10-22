# -*- coding: utf-8 -*-
"""
@author: peterpiperpickedpeppers
Description: Creates the event data folder within the project.
"""

from pathlib import Path

def create_tournament_folder(folder_name):
    """
    Creates folder for Tournament in the "data" directory of the project directory. If folder already exists, does nothing but return the path.
    
    Args:
        folder_name (str): Name of the folder to create based on the eventName globals variable.
    
    Returns:
        Path: The path to the newly created folder.
    """

    # get project_root
    project_root = Path(__file__).resolve().parent.parent
    
    # define path to data folder
    data_folder = project_root / "data"
    
    # define new folder path
    new_folder_path = data_folder / folder_name
    
    # create folder if it doesn't already exist
    new_folder_path.mkdir(parents=True, exist_ok=True)

    print(f"{folder_name} created at: {new_folder_path}")
    
    return str(new_folder_path)
