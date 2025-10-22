#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : peterpiperpickedpeppers

import os
import time
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

COOKIE = (
    'FunctionalCookie=false; AnalyticalCookie=false; CookieConsent=true; __RequestVerificationToken=k6JNLh-JBNzJ2hL2T8k5lwDOq7IMhxxQyfEn8yyEPOafwOgA47m621A70_QatTqQv8EfY737XEOwPf9Ur8k7sejq-pk1; _gid=GA1.2.91976642.1761002020; .AspNet.ApplicationCookie=oZL76dKIOTATpvonSpfMxHannyLsdM_sdxdisaMmRzUojX8rYhwnlvGn9HD0GEBGqBaIH22XTczkvkCtdgaSw0ezUr4yLxsPizIxxriaY3Yix_uI93gE_FaU8fg11IuJOI8hJgf97gaPnDW-s2xi1okD3oBVcG4R6FilTxVGSNRU0HDnO8pRTpG9Rds29VTgPSZHZDgj45F3lBxbL9aWHeel43La7Saa8coMFV5Iv_ZHmWd4paYsQyxhGsNGiFBQrY49A6sfbcCniqpxjYSylqI4gXadwe8I8qbbkHovxEnIbr9nis9bfwoZgvMIDynDxBfzJ-A0vin2E6FqoUI9TPpOZ6AWHWQNQITPE34Tn1qw1tV-jVu1Z8HlIDt3RaqsbbjqFKbR3DpVTNR1zbZC6cs_gi_S-TKllJFSyZAS9FvasJI3fYyhH4I8QCrfIm-8euYnpJFg2vf46a4QSrMLJKw8du_NGWynwS9AzNI0E8C_luQZ1NCBIXuSL5rTfnQjmIsg5_RuU8rmLSFu70RxgFghQ94; _dd_s=aid=2a9bd686-09f6-4efd-8fa5-4ea650eb85bc&rum=0&expire=1761113374893; _gat_gtag_UA_162951615_1=1; _ga_0SLSY5ZVGM=GS2.1.s1761112474$o49$g1$t1761112475$j59$l0$h0; _ga=GA1.1.1568628741.1755653966'
)

# ======= CONFIG =======
EVENT_ID = 248718
#COOKIE = r"""<PASTE THE ENTIRE Cookie HEADER VALUE HERE (no ^ chars)>"""
# OUT_DIR = r""  # e.g., r"C:\Users\you\Desktop" or "" to skip saving
PAGE_SIZE = 400
REQUEST_DELAY = 0.15
# ======================

URL_STANDINGS = "https://melee.gg/Standing/GetRoundStandings"
URL_EVENT     = f"https://melee.gg/Standing/Event/{EVENT_ID}"

# ---------- DataTables payload (matches your working fetcher) ----------
def _make_payload(round_id: int, start: int, length: int) -> dict:
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

# ---------- CSRF helper (preflight fetch; same approach as your working script) ----------
def _maybe_get_csrf_header(session: requests.Session, event_id: int) -> dict:
    try:
        r = session.get(f"https://melee.gg/Standing/Event/{event_id}", timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        inp = soup.find("input", {"name": "__RequestVerificationToken"})
        if inp and inp.get("value"):
            return {"RequestVerificationToken": inp["value"]}
        meta = soup.find("meta", {"name": "__RequestVerificationToken"})
        if meta and meta.get("content"):
            return {"RequestVerificationToken": meta["content"]}
    except Exception:
        pass
    return {}

# ---------- session factory (matches your working headers) ----------
def make_session(event_id: int, cookie: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://melee.gg",
        "Referer": f"https://melee.gg/Standing/Event/{event_id}",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0",
    })
    # Inject CSRF header if present (preflight GET happens inside helper)
    s.headers.update(_maybe_get_csrf_header(s, event_id))
    return s

# ---------- discover round IDs from the Standing/Event page (correct source) ----------
def get_round_ids(session: requests.Session, event_id: int) -> list[int]:
    r = session.get(f"https://melee.gg/Tournament/View/{event_id}", timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    btns = soup.select("#standings-round-selector-container .round-selector")
    if not btns:
        btns = soup.select("#pairings-round-selector-container .round-selector")
    ids = []
    for b in btns:
        rid = (b.get("data-id") or "").strip()
        if rid.isdigit():
            ids.append(int(rid))
    # newest → oldest
    ids.reverse()
    return ids

# ---------- probing (full payload; also checks recordsTotal/Filtered) ----------
def probe_round(session: requests.Session, round_id: int) -> tuple[bool, dict]:
    for length in (1, 25):  # try tiny page, then a small page
        r = session.post(URL_STANDINGS, data=_make_payload(round_id, start=0, length=length), timeout=30)
        status = r.status_code
        try:
            j = r.json()
        except Exception:
            j = {}
        rows = j.get("data") or []
        total = j.get("recordsTotal") or j.get("recordsFiltered") or 0
        has = bool(rows) or (isinstance(total, int) and total > 0)
        print(f"probe rid={round_id} len={length} status={status} rows={len(rows)} total={total}")
        if has or status >= 400:
            return has, j
    return False, j

# ---------- full fetch (paginated) ----------
def fetch_full_round(session: requests.Session, round_id: int, page_size: int = PAGE_SIZE, delay: float = REQUEST_DELAY) -> pd.DataFrame:
    all_rows, start, page = [], 0, 1
    while True:
        r = session.post(URL_STANDINGS, data=_make_payload(round_id, start=start, length=page_size), timeout=30)
        r.raise_for_status()
        j = r.json()
        chunk = j.get("data", [])
        if not chunk:
            break
        all_rows.extend(chunk)
        print(f"Fetched page {page}: {len(chunk)} rows (start={start})")
        start += page_size
        page += 1
        time.sleep(delay)
        if len(chunk) < page_size:
            break
    return pd.DataFrame(all_rows)

# ---------- main ----------
if __name__ == "__main__":
    if not COOKIE.strip():
        raise SystemExit("Missing COOKIE. Paste your Cookie header into COOKIE above.")

    s = make_session(EVENT_ID, COOKIE)

    # 1) discover round ids (newest → oldest)
    round_ids = get_round_ids(s, EVENT_ID)
    print("Round IDs (newest→oldest):", round_ids)

    # 2) probe newest → oldest and stop at the first with data
    hit_id, hit_meta = None, None
    for rid in round_ids:
        ok, meta = probe_round(s, rid)
        if ok:
            hit_id, hit_meta = rid, meta
            print(f"\n✅ First round with data: {hit_id}")
            break

    if hit_id is None:
        # quick diagnostic
        print("\nNo rounds reported data on probe. Last meta snippet:")
        print(json.dumps((hit_meta or {}) if isinstance(hit_meta, dict) else {}, indent=2)[:1000])
        raise SystemExit("Re-copy a fresh Cookie from DevTools and retry.")

    # 3) fetch that round fully
    df = fetch_full_round(s, hit_id, page_size=PAGE_SIZE, delay=REQUEST_DELAY)
    print(f"\nTotal rows fetched for round {hit_id}: {len(df)}")

    # # 4) optional save
    # if OUT_DIR:
    #     os.makedirs(OUT_DIR, exist_ok=True)
    #     out_path = os.path.join(OUT_DIR, f"standings_round_{hit_id}.csv")
    #     df.to_csv(out_path, index=False, encoding="utf-8-sig")
    #     print(f"Saved: {out_path}")
