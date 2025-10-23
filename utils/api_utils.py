#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers

from bs4 import BeautifulSoup
import requests
import os
import pandas as pd
import time
from dotenv import load_dotenv
from typing import Any
import json, ast

load_dotenv()

# standings api utils
def standings_make_payload(round_id: int, start: int, length: int) -> dict:
    """Mirror the full DataTables payload captured from DevTools (prevents 500s)."""
    return {
        "draw": "1",

        "columns[0][data]": "Rank",
        "columns[0][name]": "Rank",
        "columns[0][searchable]": "true",
        "columns[0][orderable]": "true",
        "columns[0][search][value]": "",
        "columns[0][search][regex]": "false",

        "columns[1][data]": "Player",
        "columns[1][name]": "Player",
        "columns[1][searchable]": "false",
        "columns[1][orderable]": "false",
        "columns[1][search][value]": "",
        "columns[1][search][regex]": "false",

        "columns[2][data]": "Decklists",
        "columns[2][name]": "Decklists",
        "columns[2][searchable]": "false",
        "columns[2][orderable]": "false",
        "columns[2][search][value]": "",
        "columns[2][search][regex]": "false",

        "columns[3][data]": "MatchRecord",
        "columns[3][name]": "MatchRecord",
        "columns[3][searchable]": "false",
        "columns[3][orderable]": "false",
        "columns[3][search][value]": "",
        "columns[3][search][regex]": "false",

        "columns[4][data]": "GameRecord",
        "columns[4][name]": "GameRecord",
        "columns[4][searchable]": "false",
        "columns[4][orderable]": "false",
        "columns[4][search][value]": "",
        "columns[4][search][regex]": "false",

        "columns[5][data]": "Points",
        "columns[5][name]": "Points",
        "columns[5][searchable]": "true",
        "columns[5][orderable]": "true",
        "columns[5][search][value]": "",
        "columns[5][search][regex]": "false",

        "columns[6][data]": "OpponentMatchWinPercentage",
        "columns[6][name]": "OpponentMatchWinPercentage",
        "columns[6][searchable]": "false",
        "columns[6][orderable]": "true",
        "columns[6][search][value]": "",
        "columns[6][search][regex]": "false",

        "columns[7][data]": "TeamGameWinPercentage",
        "columns[7][name]": "TeamGameWinPercentage",
        "columns[7][searchable]": "false",
        "columns[7][orderable]": "true",
        "columns[7][search][value]": "",
        "columns[7][search][regex]": "false",

        "columns[8][data]": "OpponentGameWinPercentage",
        "columns[8][name]": "OpponentGameWinPercentage",
        "columns[8][searchable]": "false",
        "columns[8][orderable]": "true",
        "columns[8][search][value]": "",
        "columns[8][search][regex]": "false",

        "columns[9][data]": "FinalTiebreaker",
        "columns[9][name]": "FinalTiebreaker",
        "columns[9][searchable]": "false",
        "columns[9][orderable]": "true",
        "columns[9][search][value]": "",
        "columns[9][search][regex]": "false",

        "columns[10][data]": "OpponentCount",
        "columns[10][name]": "OpponentCount",
        "columns[10][searchable]": "true",
        "columns[10][orderable]": "true",
        "columns[10][search][value]": "",
        "columns[10][search][regex]": "false",

        "order[0][column]": "0",
        "order[0][dir]": "asc",
        "start": str(start),
        "length": str(length),
        "search[value]": "",
        "search[regex]": "false",
        "roundId": str(round_id),
    }

def standings_maybe_get_csrf_header(session: requests.Session, event_id: int) -> dict:
    """
    Try to fetch an anti-forgery token from the event page.
    If found, return {"RequestVerificationToken": token}; otherwise {}.
    """
    try:
        r = session.get(f"https://melee.gg/Standing/Event/{event_id}", timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # common locations for CSRF token
        inp = soup.find("input", {"name": "__RequestVerificationToken"})
        if inp and inp.get("value"):
            return {"RequestVerificationToken": inp["value"]}
        meta = soup.find("meta", {"name": "__RequestVerificationToken"})
        if meta and meta.get("content"):
            return {"RequestVerificationToken": meta["content"]}
    except Exception:
        pass
    return {}

def fetch_round_standings(round_id: int, event_id: int, page_size: int = 100, delay_s: float = 0.2) -> pd.DataFrame:
    cookie = os.environ.get("MELEE_COOKIE")
    if not cookie:
        raise RuntimeError("Set MELEE_COOKIE with your Cookie header from DevTools.")

    s = requests.Session()
    s.headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://melee.gg",
        "Referer": f"https://melee.gg/Standing/Event/{event_id}",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie,
    })
    s.headers.update(standings_maybe_get_csrf_header(s, event_id))

    all_rows = []
    start = 0
    page_num = 1

    while True:
        r = s.post(os.environ.get("MELEE_GET_STANDINGS_URL"), data=standings_make_payload(round_id, start=start, length=page_size), timeout=30) # type: ignore
        if r.status_code >= 400:
            raise RuntimeError(f"Page fetch failed at start={start} ({r.status_code}).\n{r.text[:1000]}")
        j = r.json()
        rows = j.get("data", j)

        n = len(rows)
        if not n:
            break

        all_rows.extend(rows)
        print(f"Fetched page {page_num}: {n} rows (start={start})")

        # advance; if server caps 'length' keep paging past that cap
        start += page_size
        page_num += 1
        time.sleep(delay_s)

        # stop when a short page is returned (means no more data)
        if n < page_size:
            break

    return pd.DataFrame(all_rows)

def standings_extract_display_names(team_entry: Any) -> str | None:
    """
    Return a comma-separated string of player display names from a Team object.
    Accepts:
      - dict (already-parsed team payload)
      - str (JSON or Python-literal dict)
      - None / NaN-like -> None
    Tries DisplayName, then DisplayNameLastFirst, then Username, then Name.
    """
    if team_entry is None:
        return None

    # Handle NaN-like values without importing numpy
    try:
        # floats can be NaN; NaN != NaN
        if isinstance(team_entry, float) and team_entry != team_entry:
            return None
    except Exception:
        pass

    team: dict[str, Any] | None = None

    if isinstance(team_entry, dict):
        team = team_entry
    elif isinstance(team_entry, str):
        s = team_entry.strip()
        if not s:
            return None
        # Try JSON first, then Python-literal (handles single quotes)
        try:
            team = json.loads(s)
        except json.JSONDecodeError:
            try:
                team = ast.literal_eval(s)
            except Exception:
                return None
    else:
        return None

    if not isinstance(team, dict):
        return None

    players = team.get("Players") or team.get("players")

    # Sometimes the payload is a single player dict instead of a Team dict
    if isinstance(players, dict):
        players = [players]

    if not isinstance(players, list):
        return None

    names: list[str] = []
    for p in players:
        if not isinstance(p, dict):
            continue
        name = (
            p.get("DisplayName")
            or p.get("DisplayNameLastFirst")
            or p.get("Username")
            or p.get("Name")
        )
        if name:
            names.append(str(name))

    return ", ".join(names) if names else None

def get_round_ids(session: requests.Session, event_id: int, mode: str = "standings") -> list[int]:
    """
    Fetch round IDs from a Melee tournament page.

    Args:
        session (requests.Session): Active session with headers/cookies.
        event_id (int): The tournament's event ID.
        mode (str): Either "standings" or "pairings" — determines which selector to scrape.

    Returns:
        list[int]: Round IDs in newest→oldest order.
    """
    # Validate argument early
    if mode not in {"standings", "pairings"}:
        raise ValueError("mode must be 'standings' or 'pairings'")

    r = session.get(f"https://melee.gg/Tournament/View/{event_id}", timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Choose the right selector based on mode
    if mode == "standings":
        btns = soup.select("#standings-round-selector-container .round-selector")
    else:
        btns = soup.select("#pairings-round-selector-container .round-selector")

    ids = []
    for b in btns:
        rid = (b.get("data-id") or "").strip()  # type: ignore
        if rid.isdigit():
            ids.append(int(rid))

    # Return newest → oldest
    ids.reverse()
    return ids

# pairings api utils
def parse_result_string(result: str):
    """
    Parses the ResultString column to determine the outcome.
    Return (winner_name, is_draw, is_bye)
    winner_name is None on draw/bye.
    """
    if not isinstance(result, str):
        return (None, False, False)
    s = result.strip()
    if "was assigned a bye" in s:
        # e.g. "doejurko was assigned a bye"
        who = s.replace(" was assigned a bye", "").strip()
        return (who, False, True)
    if "Draw" in s or "-0-3 Draw" in s or "0-0-3" in s:
        return (None, True, False)
    # e.g. "Sam Clayton won 2-0-0"
    if " won " in s:
        return (s.split(" won ", 1)[0].strip(), False, False)
    return (None, False, False)

def extract_competitor(comp: dict):
    """
    From one competitor dictionary (from the JSON row), pull player name and their first decklist name.
    Returns (name, deck)
    """
    # Player name (DisplayName preferred)
    name = None
    try:
        players = comp.get("Team", {}).get("Players", [])
        if players and isinstance(players, list):
            p = players[0] or {}
            name = p.get("DisplayName") or p.get("DisplayNameLastFirst") or p.get("Username")
    except Exception:
        pass

    # Decklist name (first decklist if present)
    deck = None
    try:
        decks = comp.get("Decklists", [])
        if decks and isinstance(decks, list):
            deck = decks[0].get("DecklistName")
    except Exception:
        pass

    return name, deck

def process_raw_pairings_list(raw_pairings_list: list) -> pd.DataFrame:
    """
    Convert the aggregated list of Melee match dictionaries into a rectangular DF,
    performing cleanup and column standardization.
    """
    # NOTE: This function relies on parse_result_string and extract_competitor
    # being available in the same module scope, which is why we moved them here.
    
    rows = []
    for m in raw_pairings_list:
        # The raw list already contains the 'RoundId' which was injected during fetching
        round_id = m.get("RoundId")
        result = m.get("ResultString")
        winner_name, is_draw, is_bye = parse_result_string(result)

        # Competitors list comes from the 'Competitors' key in the raw match dict
        comps = m.get("Competitors", []) or [] 
        
        # Normalize two sides; some entries (bye) have only one competitor
        if len(comps) == 2:
            p1_name, p1_deck = extract_competitor(comps[0])
            p2_name, p2_deck = extract_competitor(comps[1])
        elif len(comps) == 1:
            p1_name, p1_deck = extract_competitor(comps[0])
            p2_name, p2_deck = None, None
        else:
            # Skip totally malformed rows (or rows with 0 or >2 competitors)
            continue

        # Decide outcome/winning deck
        if is_bye:
            outcome = "Bye"
            winning_deck = p1_deck if winner_name == p1_name else None
        elif is_draw:
            outcome = "Draw"
            winning_deck = None
        else:
            if winner_name and winner_name == p1_name:
                outcome = f"{p1_name} won"
                winning_deck = p1_deck
            elif winner_name and winner_name == p2_name:
                outcome = f"{p2_name} won"
                winning_deck = p2_deck
            else:
                # Unknown/edge case – keep original string
                outcome = result or "Unknown"
                winning_deck = None

        rows.append({
            "RoundId": round_id,
            "TableNumber": m.get("TableNumberDescription") or m.get("TableNumber"),
            "Player": p1_name,
            "PlayerDeck": p1_deck,
            "Opponent": p2_name,
            "OpponentDeck": p2_deck,
            "Outcome": outcome,
            "WinningDeck": winning_deck,
            "ResultString": result,
        })

    df = pd.DataFrame(rows)
    
    # --- Robust Table Number Extraction for Sorting ---
    with pd.option_context("mode.chained_assignment", None):
        # Convert original column to string
        table_series = df["TableNumber"].astype(str)
        
        # 1. Attempt to extract the number from HTML (TableNumberDescription)
        extracted_from_html = table_series.str.extract(r'>(\d+)<', expand=False)
        
        # 2. Fallback to the original string if HTML extraction failed (e.g., if it was just '10')
        df["Table_Numeric"] = extracted_from_html.fillna(table_series)
        
        # 3. Final conversion to numeric, coercing any non-numeric value to NaN
        df["Table_Numeric"] = pd.to_numeric(df["Table_Numeric"], errors="coerce")

    # Fill NaNs with a large sentinel value (9999) so they sort last
    df["Table_Numeric"] = df["Table_Numeric"].fillna(9999).astype(int) 

    # Sort by the numeric Table column
    df = df.sort_values(["RoundId", "Table_Numeric", "Player"], na_position="last").reset_index(drop=True)
    
    # Rename the cleaned column
    df = df.rename(columns={'Table_Numeric': 'TableNumber_Cleaned'})
    
    # Select final columns 
    final_cols = ['RoundId', 'TableNumber_Cleaned', 'Player', 'PlayerDeck', 'Opponent', 'OpponentDeck', 'Outcome', 'WinningDeck', 'ResultString']
    return df[final_cols]

def make_payload(start: int, length: int) -> dict:
    """Generates the DataTables payload with updated start/length values."""
    # (Payload structure remains the same)
    return {
        'draw': '3', 
        'columns[0][data]': 'TableNumber',
        'columns[0][name]': 'TableNumber',
        'columns[0][searchable]': 'true',
        'columns[0][orderable]': 'true',
        'columns[0][search][value]': '',
        'columns[0][search][regex]': 'false',
        'columns[1][data]': 'PodNumber',
        'columns[1][name]': 'PodNumber',
        'columns[1][searchable]': 'true',
        'columns[1][orderable]': 'true',
        'columns[1][search][value]': '',
        'columns[1][search][regex]': 'false',
        'columns[2][data]': 'Teams',
        'columns[2][name]': 'Teams',
        'columns[2][searchable]': 'false',
        'columns[2][orderable]': 'false',
        'columns[2][search][value]': '',
        'columns[2][search][regex]': 'false',
        'columns[3][data]': 'Decklists',
        'columns[3][name]': 'Decklists',
        'columns[3][searchable]': 'false',
        'columns[3][orderable]': 'false',
        'columns[3][search][value]': '',
        'columns[3][search][regex]': 'false',
        'columns[4][data]': 'ResultString',
        'columns[4][name]': 'ResultString',
        'columns[4][searchable]': 'false',
        'columns[4][orderable]': 'false',
        'columns[4][search][value]': '',
        'columns[4][search][regex]': 'false',
        'order[0][column]': '0',
        'order[0][dir]': 'asc',
        'start': str(start), 
        'length': str(length), 
        'search[value]': '',
        'search[regex]': 'false'
    }




