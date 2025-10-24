#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers


import requests
import json
import os
import time
import pandas as pd
from dotenv import load_dotenv
from utils.api_utils import (
    parse_result_string,
    extract_competitor,
    process_raw_pairings_list,
    make_payload,
    get_round_ids,
)
from pathlib import Path
import re
import time
from datetime import datetime

load_dotenv()

# configuration (allow overrides via environment variables)
EVENT_ID = int(os.environ.get("EVENT_ID", 248718))
ROUND_IDS = get_round_ids(requests.Session(), EVENT_ID, mode="pairings")
BASE_URL = "https://melee.gg/Match/GetRoundMatches/{round_id}"
# default output into data/ unless orchestrated into an event-specific folder
base_data_dir = Path(__file__).resolve().parents[1] / "data"
event_data_dir = Path(os.environ.get("EVENT_DATA_DIR", base_data_dir))
matchups_dir = event_data_dir / "matchups"
matchups_dir.mkdir(parents=True, exist_ok=True)

# include event name in filename and write into the event root (data/<event>)
event_name = os.environ.get("EVENT_NAME", "event")
# sanitize for filesystem
sanitized_event = re.sub(r'[<>:"/\\|?*]', '_', event_name)
OUTPUT_CSV_FILE = event_data_dir / f"{sanitized_event} pairings.csv"
COOKIE = os.environ.get("MELEE_COOKIE")
PAGE_SIZE = int(os.environ.get("PAGE_SIZE") or 400)
DELAY_S = float(os.environ.get("DELAY_S") or 1)

# main fetching logic

def fetch_all_rounds_data():
    """Iterates through all ROUND_IDS and fetches all associated pairings."""
    if not COOKIE:
        print("FATAL: MELEE_COOKIE environment variable is not set.")
        print("Please set it in your .env file with the full, fresh cookie string.")
        return

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": COOKIE,
    }
    
    all_rounds_rows = []
    
    print(f"Starting pipeline for {len(ROUND_IDS)} rounds.")
    print("-" * 50)
    
    for round_id in ROUND_IDS:
        url = BASE_URL.format(round_id=round_id)
        # Update referer for the current round
        headers["Referer"] = f"https://melee.gg/Pairing/Round/{round_id}"
        
        start = 0
        page_num = 1
        round_records = 0
        
        while True:
            payload = make_payload(start=start, length=PAGE_SIZE) # type: ignore
            
            try:
                print(f"Round {round_id} - Fetching page {page_num} (start={start})...")
                response = requests.post(url, data=payload, headers=headers, timeout=30)
                
                raw_content = response.text
                response.raise_for_status()

                if raw_content.strip().startswith("<!DOCTYPE html>"):
                    print(f"ERROR: Round {round_id} failed authentication. Check cookie.")
                    break

                json_data = response.json()
                rows = json_data.get("data", [])
                n_fetched = len(rows)

                if n_fetched == 0:
                    break

                # Inject the Round ID into each row before appending
                for row in rows:
                    row['RoundId'] = round_id
                    
                all_rounds_rows.extend(rows)
                round_records += n_fetched
                
                # Stop condition
                if n_fetched < PAGE_SIZE: # type: ignore
                    break
                    
                start += PAGE_SIZE # type: ignore
                page_num += 1
                time.sleep(DELAY_S)  # type: ignore

            except requests.exceptions.RequestException as e:
                print(f"Request failed for Round {round_id} on page {page_num}: {e}")
                break

            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode JSON for Round {round_id}: {e}")
                break
        
        print(f"-> Finished Round {round_id}. Total records collected: {round_records}")
        time.sleep(1) # Longer delay between rounds
        
    # Final step: Convert all collected data to a DataFrame and save
    total_records = len(all_rounds_rows)
    print("\n" + "=" * 50)
    print(f"DATA COLLECTION COMPLETE. Total pairings collected: {total_records}")
    print("=" * 50)

    if all_rounds_rows:
        try:
            # 1. Process the raw list using the imported robust logic
            df_clean = process_raw_pairings_list(all_rounds_rows)
            print("Data cleaning and feature extraction complete.")

            # 2. Save to CSV
            df_clean.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8')
            print(f"SUCCESS! Cleaned data saved to: {OUTPUT_CSV_FILE}")

        except Exception as e:
            # Using the new variable name 'df_clean' for clarity if the processing failed late
            print(f"FATAL ERROR during DataFrame processing or saving: {e}")
            # If pandas conversion fails, save the raw list to JSON as a backup
            with open("backup_raw_data.json", "w", encoding="utf-8") as f:
                json.dump(all_rounds_rows, f, indent=4)
            print("Raw data saved to backup_raw_data.json.")
    else:
        print("No data collected successfully.")

    return total_records


if __name__ == "__main__":
    start_ts = time.time()
    total = fetch_all_rounds_data()
    duration = time.time() - start_ts
    # append simple log
    try:
        logs_dir = Path(os.environ.get("EVENT_DATA_DIR", base_data_dir)) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.utcnow().isoformat() + "Z"
        log_line = f"{now} | script=fetch_pairings_api | event={sanitized_event} | event_id={EVENT_ID} | duration_s={duration:.3f} | rows={total} | out={OUTPUT_CSV_FILE}"
        with (logs_dir / "fetch_pairings_api.log").open("a", encoding="utf-8") as fh:
            fh.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write pairings log: {e}")