#!/usr/bin/env python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers

import os
import ast
from pathlib import Path
from dotenv import load_dotenv
from utils.api_utils import (
    standings_make_payload,
    standings_maybe_get_csrf_header,
    fetch_round_standings,
    standings_extract_display_names,
    get_round_ids,
)
import requests
import time
from datetime import datetime

load_dotenv()


if __name__ == "__main__":
    # Allow overriding via environment variables when orchestrating multiple scripts
    event = os.environ.get("EVENT_NAME", "PT EoE 2025")
    EVENT_ID = int(os.environ.get("EVENT_ID", 355905))
    PAGE_SIZE = int(os.environ.get("PAGE_SIZE") or 400)

    # timing and logging
    start_ts = time.time()
    rows_written = 0
    out_csv = None
    for round_id in get_round_ids(requests.Session(), EVENT_ID, mode="standings"):
        print(f"Fetching round ID: {round_id}")

        df = fetch_round_standings(round_id, EVENT_ID, page_size=PAGE_SIZE)  # type: ignore
        print(f"Total rows fetched: {len(df)}")

        if not df.empty:
            # Add PlayerName column from the Team column
            df["PlayerName"] = df["Team"].apply(standings_extract_display_names)

            # Extract Decklist GUID into its own column for downstream processing
            def _extract_guid(cell):
                # handle already-dict
                if isinstance(cell, dict):
                    # Decklists may be a dict or nested; try common keys
                    return cell.get("DecklistId") or cell.get("DecklistID") or cell.get("decklistId")
                # handle list of dicts: take first dict that has a DecklistId
                if isinstance(cell, list):
                    for item in cell:
                        if isinstance(item, dict):
                            val = item.get("DecklistId") or item.get("DecklistID") or item.get("decklistId")
                            if val:
                                return val
                    return None
                # handle stringified dict/list
                if isinstance(cell, str) and cell.strip():
                    try:
                        parsed = ast.literal_eval(cell)
                    except Exception:
                        return None
                    return _extract_guid(parsed)

            decklists_col = df.get("Decklists")
            if decklists_col is None:
                df["decklist_guid"] = None
            else:
                df["decklist_guid"] = decklists_col.apply(_extract_guid)

            # Move PlayerName to the front
            cols = ["PlayerName"] + [c for c in df.columns if c != "PlayerName"]
            df = df[cols]

            # Save into the repository `data/` folder (or into an event-specific folder
            # when orchestrated via MAIN). Respect EVENT_DATA_DIR if provided.
            base_data_dir = Path(__file__).resolve().parents[1] / "data"
            event_data_dir = Path(os.environ.get("EVENT_DATA_DIR", base_data_dir / event))
            # write directly to the event root (data/<event>) per user request
            event_data_dir.mkdir(parents=True, exist_ok=True)

            # include event name in filename
            raw_event_name = os.environ.get("EVENT_NAME", event)
            # sanitize
            import re
            sanitized_event = re.sub(r'[<>:"/\\|?*]', '_', raw_event_name)
            out_csv = event_data_dir / f"{sanitized_event} standings round_{round_id}.csv"
            df.to_csv(out_csv, index=False, encoding="utf-8-sig")
            print(f"Saved: {out_csv}\n")
            rows_written = len(df)
            break

    # write a small completion log with timestamp and duration
    try:
        logs_dir = Path(os.environ.get("EVENT_DATA_DIR", Path(__file__).resolve().parents[1] / "data" / event)) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.utcnow().isoformat() + "Z"
        duration = time.time() - start_ts
        log_line = f"{now} | script=fetch_standings_api | event={sanitized_event} | event_id={EVENT_ID} | duration_s={duration:.3f} | rows={rows_written} | out={out_csv}"
        with (logs_dir / "fetch_standings_api.log").open("a", encoding="utf-8") as fh:
            fh.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write standings log: {e}")
# -*- coding: utf-8 -*-
