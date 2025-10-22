#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers

"""
Fetches pairing data from an external API and saves it to a local JSON file."""

import json
import requests
import pandas as pd
import ast
import numpy as np
import time
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

# URL = "https://melee.gg/Standing/GetRoundStandings"

# COOKIE = "FunctionalCookie=false; AnalyticalCookie=false; CookieConsent=true; __RequestVerificationToken=k6JNLh-JBNzJ2hL2T8k5lwDOq7IMhxxQyfEn8yyEPOafwOgA47m621A70_QatTqQv8EfY737XEOwPf9Ur8k7sejq-pk1; _gid=GA1.2.91976642.1761002020; .AspNet.ApplicationCookie=acMpLOsr0bI1nz-U3alnn8iwMoQkeB24wpBAETnGJdVOsVMYzEQLrsVie1Xpx0Caz8S2HEmet3IpPmjWoQxqwXZ2qaebnGbMX8olsg-rinv5QJtAzftgeb1dEumek3dpvlWpFAjk7a8mQqCb1GONxEYsCUVUJygEnYjoLDY5tp4DhTRuicFaE-qGOEZvZPXSQTCwChA1ei7OUw91zS8K_uSmBMl-AJQ5_CLxZ4I0niq9Zn8OYCx6EBI_BWCmQH-pPYOWjdu-PjqrMnQg2EH3uNvcIvWkxzXcc6-ZCRzJxFRdOt8kjUpYucB1xad9FWCQ7ZGUtTh5rCYqLMNII6BrgozzUOU7EZVcbUZ3IJbXfwUQDKzZBKoJuR5KogNd_dxu9JLEtbl609LCIgXIdQ9GQTQ6TdQMD9GL1MlxFI5nFJQSlY0ganmWnM6ppk0pmlzDY3BuKs4FaygoJWzb-N5i35LuxaAIEF0Awq1kFAub6dLDsoq4L14Z2q3WONI-4zGymlVwYqPo_VDho3bhNMjryMc1gNE; _ga=GA1.1.1568628741.1755653966; _ga_0SLSY5ZVGM=GS2.1.s1761016228$o41$g1$t1761016509$j59$l0$h0; _dd_s=aid=2a9bd686-09f6-4efd-8fa5-4ea650eb85bc&rum=0&expire=1761017410057"

"""
Fetch full round standings from melee.gg DataTables endpoint with pagination.
- Sends full DataTables payload (prevents server 500s)
- Optionally adds RequestVerificationToken header (if present on event page)
- Paginates using start/length
- Writes CSV

"""

# load env vars from .env
load_dotenv()

def _make_payload(round_id: int, start: int, length: int) -> dict:
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

def _maybe_get_csrf_header(session: requests.Session, event_id: int) -> dict:
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
    s.headers.update(_maybe_get_csrf_header(s, event_id))

    all_rows = []
    start = 0
    page_num = 1

    while True:
        r = s.post(os.environ.get("MELEE_GET_STANDINGS_URL"), data=_make_payload(round_id, start=start, length=page_size), timeout=30)
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


if __name__ == "__main__":
    # Set these
    event = "RC Houston"
    EVENT_ID = 248718
    ROUND_ID = 865063
    PAGE_SIZE = 400    # try 100–500; if issues, drop to 25 (site default)

    df = fetch_round_standings(ROUND_ID, EVENT_ID, page_size=PAGE_SIZE)
    print(f"\nTotal rows fetched: {len(df)}")

    def extract_display_names(team_entry):
        """Return 'DisplayName' for each player in Team; handles dict or string."""
        if team_entry is None or (isinstance(team_entry, float) and np.isnan(team_entry)):
            return None
    
        team = None
    
        # Case 1: already a dict
        if isinstance(team_entry, dict):
            team = team_entry
    
        # Case 2: JSON-like string (single quotes) -> try json, then ast
        elif isinstance(team_entry, str):
            s = team_entry.strip()
            if not s:
                return None
            try:
                team = json.loads(s)  # works if double-quoted JSON
            except json.JSONDecodeError:
                try:
                    team = ast.literal_eval(s)  # handles Python-style dict with single quotes
                except Exception:
                    return None
        else:
            return None
    
        players = team.get("Players") or team.get("players") or []
        if not isinstance(players, list):
            return None
    
        names = []
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
                names.append(name)
    
        if not names:
            return None
    
        # If it’s always 1v1, you’ll just get a single name; join supports teams too.
        return ", ".join(names)
    
    # Apply
    df["PlayerName"] = df["Team"].apply(extract_display_names)

    cols = ['PlayerName'] + [c for c in df.columns if c != 'PlayerName']
    df = df[cols]

    # Save next to your repo or wherever you like
    out_csv = fr"C:\Users\jjwey\OneDrive\Desktop\{event} round_{ROUND_ID}_standings222.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_csv}")
