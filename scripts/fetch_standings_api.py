#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers


from dotenv import load_dotenv
from utils.api_utils import standings_make_payload, standings_maybe_get_csrf_header, fetch_round_standings, standings_extract_display_names, get_round_ids
import requests

load_dotenv()

if __name__ == "__main__":
    event = "PT EoE 2025"
    EVENT_ID = 355905
    PAGE_SIZE = 400

    for round_id in get_round_ids(requests.Session(), EVENT_ID, mode="standings"):
        print(f"Fetching round ID: {round_id}")
        
        df = fetch_round_standings(round_id, EVENT_ID, page_size=PAGE_SIZE)
        print(f"Total rows fetched: {len(df)}")

        if not df.empty:          
            # Add PlayerName column from the Team column
            df["PlayerName"] = df["Team"].apply(standings_extract_display_names)

            # Move PlayerName to the front
            cols = ["PlayerName"] + [c for c in df.columns if c != "PlayerName"]
            df = df[cols]

            out_csv = fr"C:\Users\jjwey\OneDrive\Desktop\{event} round_{round_id}_standings.csv"
            df.to_csv(out_csv, index=False, encoding="utf-8-sig")
            print(f"Saved: {out_csv}\n")
            break
