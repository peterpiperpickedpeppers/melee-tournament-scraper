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

def extract_display_names(team_entry: Any) -> str | None:
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