#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers

import os
import ast
import re
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from utils.api_utils import (
    standings_make_payload,
    standings_maybe_get_csrf_header,
    fetch_round_standings,
    standings_extract_display_names,
    get_round_ids,
    classify_event_round_ids,
)
import requests
import time
from datetime import datetime, timezone

from scripts.fetch_decklists_api import DecklistScraper

load_dotenv()


def _parse_match_record(match_record):
    if match_record is None:
        return {"wins": 0, "losses": 0, "draws": 0}
    text_value = str(match_record).strip()
    if not text_value or "-" not in text_value:
        return {"wins": 0, "losses": 0, "draws": 0}
    parts = [part.strip() for part in text_value.split("-") if part.strip()]
    if len(parts) < 3:
        return {"wins": 0, "losses": 0, "draws": 0}
    try:
        return {
            "wins": int(parts[0]),
            "losses": int(parts[1]),
            "draws": int(parts[2]),
        }
    except ValueError:
        return {"wins": 0, "losses": 0, "draws": 0}


def _parse_round_number(row):
    for key in ("RoundNumber", "Round", "RoundId"):
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, (int, float)):
            return int(value)
        text_value = str(value).strip()
        if not text_value:
            continue
        match = re.search(r"(\d+)", text_value)
        if match:
            return int(match.group(1))
    return None


def _is_limited_round_row(row, event_name=None, limited_round_count=3):
    phase_name = str(row.get("PhaseName") or row.get("Phase") or "").lower()
    round_label = str(row.get("Round") or row.get("RoundNumber") or row.get("RoundId") or "").lower()
    if any(token in phase_name or token in round_label for token in ("limited", "draft", "sealed", "booster")):
        return True

    event_label = (event_name or "").lower()
    round_number = _parse_round_number(row)
    if "pt" in event_label and round_number is not None and round_number <= limited_round_count:
        return True
    return False


if __name__ == "__main__":
    # Allow overriding via environment variables when orchestrating multiple scripts
    event = os.environ.get("EVENT_NAME", "PT EoE 2025")
    EVENT_ID = int(os.environ.get("EVENT_ID", 355905))
    PAGE_SIZE = int(os.environ.get("PAGE_SIZE") or 400)
    LIMITED_ROUND_COUNT = int(os.environ.get("LIMITED_ROUND_COUNT") or 3)
    EVENT_TYPE = (os.environ.get("EVENT_TYPE") or "constructed").strip().lower()

    # timing and logging
    start_ts = time.time()
    rows_written = 0
    out_csv = None
    summary_rows = []
    player_totals = {}
    player_limited = {}
    player_deck_info = {}
    scraper = DecklistScraper()

    base_data_dir = Path(__file__).resolve().parents[1] / "data"
    event_data_dir = Path(os.environ.get("EVENT_DATA_DIR", base_data_dir / event))
    event_data_dir.mkdir(parents=True, exist_ok=True)

    raw_event_name = os.environ.get("EVENT_NAME", event)
    sanitized_event = re.sub(r'[<>:"/\\|?*]', '_', raw_event_name)

    session = requests.Session()
    round_classification = classify_event_round_ids(session, EVENT_ID, EVENT_TYPE, mode="standings")
    limited_round_ids = set(int(x) for x in round_classification.get("limited_ids", []))

    round_ids = list(reversed(get_round_ids(session, EVENT_ID, mode="standings")))
    if limited_round_ids:
        print(f"Detected limited rounds for event_type={EVENT_TYPE}: {sorted(limited_round_ids)}")
    else:
        print(f"No limited rounds detected for event_type={EVENT_TYPE}; all rounds treated as constructed")

    for round_id in round_ids:
        print(f"Fetching round ID: {round_id}")

        df = fetch_round_standings(round_id, EVENT_ID, page_size=PAGE_SIZE)  # type: ignore
        print(f"Total rows fetched: {len(df)}")

        if not df.empty:
            df["PlayerName"] = df["Team"].apply(standings_extract_display_names)

            def _extract_deck_info(cell):
                guid = ""
                archetype = ""
                if isinstance(cell, dict):
                    guid = cell.get("DecklistId") or cell.get("DecklistID") or cell.get("decklistId") or ""
                    archetype = cell.get("DecklistName") or cell.get("decklistName") or ""
                    return str(guid).strip(), str(archetype).strip()
                if isinstance(cell, list):
                    for item in cell:
                        if isinstance(item, dict):
                            g = item.get("DecklistId") or item.get("DecklistID") or item.get("decklistId") or ""
                            if g:
                                n = item.get("DecklistName") or item.get("decklistName") or ""
                                return str(g).strip(), str(n).strip()
                    return "", ""
                if isinstance(cell, str) and cell.strip():
                    try:
                        parsed = ast.literal_eval(cell)
                    except Exception:
                        return "", ""
                    return _extract_deck_info(parsed)
                return "", ""

            def _extract_guid(cell):
                guid, _ = _extract_deck_info(cell)
                return guid or None

            decklists_col = df.get("Decklists")
            if decklists_col is None:
                df["decklist_guid"] = None
            else:
                df["decklist_guid"] = decklists_col.apply(_extract_guid)

            cols = ["PlayerName"] + [c for c in df.columns if c != "PlayerName"]
            df = df[cols]

            out_csv = event_data_dir / f"{sanitized_event} standings round_{round_id}.csv"
            df.to_csv(out_csv, index=False, encoding="utf-8-sig")
            print(f"Saved: {out_csv}\n")
            rows_written += len(df)

            for _, row in df.iterrows():
                player_name_raw = str(row.get("PlayerName") or "").strip()
                if not player_name_raw:
                    continue
                player_name = scraper.normalize_player_name(player_name_raw)
                if not player_name:
                    continue

                current_totals = _parse_match_record(row.get("MatchRecord"))
                previous_totals = player_totals.get(player_name, {"wins": 0, "losses": 0, "draws": 0})
                delta = {
                    "wins": max(0, current_totals["wins"] - previous_totals.get("wins", 0)),
                    "losses": max(0, current_totals["losses"] - previous_totals.get("losses", 0)),
                    "draws": max(0, current_totals["draws"] - previous_totals.get("draws", 0)),
                }
                player_totals[player_name] = current_totals
                player_limited.setdefault(player_name, {"wins": 0, "losses": 0, "draws": 0})
                if int(round_id) in limited_round_ids:
                    player_limited[player_name]["wins"] += delta["wins"]
                    player_limited[player_name]["losses"] += delta["losses"]
                    player_limited[player_name]["draws"] += delta["draws"]

                deck_guid, deck_archetype = _extract_deck_info(row.get("Decklists"))
                if not deck_guid:
                    deck_guid = row.get("decklist_guid") or row.get("DecklistGuid") or None
                if deck_guid:
                    player_deck_info[player_name] = {
                        "decklist_guid": str(deck_guid).strip(),
                        "deck_archetype": str(deck_archetype).strip(),
                    }

    for player_name, totals in player_totals.items():
        limited = player_limited.get(player_name, {"wins": 0, "losses": 0, "draws": 0})
        summary_rows.append({
            "PlayerName": player_name,
            "wins": totals.get("wins", 0),
            "losses": totals.get("losses", 0),
            "draws": totals.get("draws", 0),
            "limited_wins": limited.get("wins", 0),
            "limited_losses": limited.get("losses", 0),
            "limited_draws": limited.get("draws", 0),
            "constructed_wins": max(0, totals.get("wins", 0) - limited.get("wins", 0)),
            "constructed_losses": max(0, totals.get("losses", 0) - limited.get("losses", 0)),
            "constructed_draws": max(0, totals.get("draws", 0) - limited.get("draws", 0)),
            "decklist_guid": player_deck_info.get(player_name, {}).get("decklist_guid", ""),
            "deck_archetype": player_deck_info.get(player_name, {}).get("deck_archetype", ""),
        })

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_path = event_data_dir / f"{sanitized_event} standings summary.csv"
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"Saved standings summary: {summary_path}")

    try:
        logs_dir = event_data_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        duration = time.time() - start_ts
        log_line = f"{now} | script=fetch_standings_api | event={sanitized_event} | event_id={EVENT_ID} | duration_s={duration:.3f} | rows={rows_written} | out={out_csv}"
        with (logs_dir / "fetch_standings_api.log").open("a", encoding="utf-8") as fh:
            fh.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write standings log: {e}")
# -*- coding: utf-8 -*-
