#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DecklistScraper: Extract card rows from deck view pages.

Fetches a deck view page, extracts cards and the player name, and optionally
saves the results in a combined CSV file.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import requests
import re
import csv
from bs4 import BeautifulSoup
import csv as _csv
from typing import Set

# Name suffixes to preserve (used in future normalization helpers)
NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
import time
from datetime import datetime, timezone


class DecklistScraper:
    """Fetch a deck view and extract card rows and the player name.

    Methods:
    - build_view_url(guid) -> str
    - fetch_into_memory(url) -> payload dict with status_code, html, soup
    - parse_cards_from_soup(soup) -> list of {card_name, qty, zone}
    - extract_player_from_soup(soup) -> player display name or ""
    - extract_cards_and_player(payload, guid) -> rows for CSV
    - process_guids(guids, save_csv) -> list rows and optional CSV file
    """

    def __init__(self, session: Optional[requests.Session] = None, view_url_template: str = "https://melee.gg/Decklist/View/{}"):
        self.session = session or requests.Session()
        self.view_url_template = view_url_template

    def build_view_url(self, guid: str) -> str:
        return self.view_url_template.format(guid)

    def fetch_into_memory(self, url: str, timeout: int = 20) -> Dict[str, Any]:
        try:
            r = self.session.get(url, timeout=timeout)
        except Exception as e:
            return {"status_code": None, "html": "", "soup": None, "error": e}
        try:
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception:
            soup = None
        return {"status_code": r.status_code, "html": r.text, "soup": soup}

    def parse_cards_from_soup(self, soup: Optional[BeautifulSoup]) -> List[Dict[str, Any]]:
        """Extract cards using heuristics (structured -> UL/LI -> text fallback).

        Returns a list of unique card dicts with combined quantities.
        """
        if soup is None:
            return []
        def parse_line(t: str, zone: str = "main") -> Optional[Dict[str, Any]]:
            s = (t or "").strip()
            if not s:
                return None
            m = re.match(r"^(\d+)[xX]?\s+(.*)$", s)
            if m:
                return {"card_name": m.group(2).strip(), "qty": int(m.group(1)), "zone": zone}
            m2 = re.match(r"^(.+?)\s+[xX](\d+)$", s)
            if m2:
                return {"card_name": m2.group(1).strip(), "qty": int(m2.group(2)), "zone": zone}
            return {"card_name": s, "qty": 1, "zone": zone}

        def detect_zone_from_element(el) -> str:
            """Detect whether an element is part of the 'side' or 'main' section.

            Heuristics:
            - If an ancestor's class or id contains 'side' or 'sideboard' -> 'side'
            - If a nearby heading (previous h1..h6) contains 'side' -> 'side'
            - Otherwise 'main'
            """
            # ancestor class/id check
            cur = el
            while cur is not None and getattr(cur, 'name', None) is not None:
                attrs = getattr(cur, 'attrs', {}) or {}
                for v in list(attrs.get('class', [])) + ([attrs.get('id')] if attrs.get('id') else []):
                    if not v:
                        continue
                    if re.search(r"side(board)?|sideboard", str(v), flags=re.I):
                        return "side"
                cur = cur.parent
            # previous heading check
            for level in range(1, 7):
                prev_h = el.find_previous(f"h{level}")
                if prev_h and re.search(r"side(board)?|sideboard", prev_h.get_text(), flags=re.I):
                    return "side"
            return "main"

        cards: List[Dict[str, Any]] = []

        # 1) If the page groups cards into categories, honor those zones
        cats = soup.select(".decklist-category")
        if cats:
            for cat in cats:
                title_el = cat.select_one(".decklist-category-title")
                zone = "side" if (title_el and re.search(r"side(board)?", title_el.get_text(), flags=re.I)) else "main"
                for rec in cat.select(".decklist-record"):
                    name_el = rec.select_one(".decklist-record-name")
                    qty_el = rec.select_one(".decklist-record-quantity")
                    if name_el:
                        name = name_el.get_text(strip=True)
                        qty = 1
                        if qty_el:
                            try:
                                qty = int(qty_el.get_text(strip=True))
                            except Exception:
                                qty = 1
                        cards.append({"card_name": name, "qty": qty, "zone": zone})

        # 2) structured .decklist-record blocks (not grouped) with zone detection
        if not cards:
            for rec in soup.select(".decklist-record"):
                name_el = rec.select_one(".decklist-record-name")
                qty_el = rec.select_one(".decklist-record-quantity")
                if name_el:
                    name = name_el.get_text(strip=True)
                    qty = 1
                    if qty_el:
                        try:
                            qty = int(qty_el.get_text(strip=True))
                        except Exception:
                            qty = 1
                    zone = detect_zone_from_element(rec)
                    cards.append({"card_name": name, "qty": qty, "zone": zone})

        # 3) UL/LI lists (use nearby heading text to guess sideboard)
        if not cards:
            for ul in soup.find_all("ul"):
                prev_h = None
                for level in range(1, 7):
                    prev_h = ul.find_previous(f"h{level}")
                    if prev_h:
                        break
                zone = "side" if (prev_h and re.search(r"side", prev_h.get_text(), flags=re.I)) else "main"
                for li in ul.find_all("li"):
                    parsed = parse_line(li.get_text(" ", strip=True), zone=zone)
                    if parsed:
                        cards.append(parsed)

        # 4) text fallback: scan lines and switch to side when 'sideboard' appears
        if not cards:
            text = soup.get_text("\n", strip=True)
            zone = "main"
            for ln in text.splitlines():
                if re.search(r"sideboard", ln, flags=re.I):
                    zone = "side"
                    continue
                parsed = parse_line(ln, zone=zone)
                if parsed:
                    cards.append(parsed)

        # combine duplicates (case-insensitive card name + zone)
        combined: Dict[tuple, Dict[str, Any]] = {}
        for r in cards:
            key = (r["card_name"].strip().lower(), r["zone"])
            if key in combined:
                combined[key]["qty"] += r["qty"]
            else:
                combined[key] = {"card_name": r["card_name"].strip(), "qty": r["qty"], "zone": r["zone"]}
        return list(combined.values())

    def extract_player_from_soup(self, soup: Optional[BeautifulSoup]) -> str:
        """Try several heuristics to find the deck owner/player name.

        Order of attempts:
        1. meta[name=description] or meta[property=og:description] -> parse "DeckTitle - Player - ..."
        2. a few page-local selectors likely to contain the owner link
        3. any profile link that doesn't look like a site header/organization link
        4. .decklist-title fallback
        """
        if soup is None:
            return ""

        # 1) Try meta description (often: "DeckTitle - Player, Name - Format")
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta:
            content = str(meta.get("content") or "").strip()
            if content:
                parts = [p.strip() for p in content.split(" - ") if p.strip()]
                if len(parts) >= 2:
                    return parts[1]

        # 2) Page-local selectors that are likely to contain the owner link
        selectors = [
            ".decklist-header a[href*='/Profile']",
            ".decklist-info a[href*='/Profile']",
            ".decklist-owner a[href*='/Profile']",
            "a.decklist-author[href*='/Profile']",
        ]
        for sel in selectors:
            a = soup.select_one(sel)
            if a and a.get_text(strip=True):
                return a.get_text(strip=True)

        # 3) Look for any /Profile link but filter out header/organization links
        for a in soup.select("a[href*='/Profile']"):
            txt = a.get_text(strip=True)
            if not txt:
                continue
            # ignore organization/dashboard style links
            if re.search(r"organization|organizations|dashboard|settings", txt, flags=re.I):
                continue
            # ignore very long values
            if len(txt) > 60:
                continue
            return txt

        # 4) fallback to a visible title element
        title = soup.select_one(".decklist-title")
        if title:
            return title.get_text(strip=True)

        return ""

    def extract_cards_and_player(self, payload: Dict[str, Any], guid: str) -> List[Dict[str, Any]]:
        soup = payload.get("soup")
        player = self.extract_player_from_soup(soup)
        player = self.normalize_player_name(player)
        cards = self.parse_cards_from_soup(soup)
        rows: List[Dict[str, Any]] = []
        for c in cards:
            rows.append({
                "player": player,
                "card_name": c["card_name"],
                "qty": c["qty"],
                "zone": c["zone"],
                "deck_guid": guid,
            })
        return rows

    def normalize_player_name(self, raw: str) -> str:
        """Normalize player display names into 'First Last' with suffix handling.

        Examples:
        - 'Hulstine, liam' -> 'Liam Hulstine'
        - 'Smith, John Jr.' -> 'John Smith Jr.'
        - 'John Smith' -> 'John Smith'
        Returns empty string if raw is falsy.
        """
        if not raw:
            return ""
        s = raw.strip()
        # canonical suffix formatting
        SUFFIX_MAP = {
            "jr": "Jr.",
            "jr.": "Jr.",
            "sr": "Sr.",
            "sr.": "Sr.",
            "ii": "II",
            "iii": "III",
            "iv": "IV",
            "v": "V",
        }

        # If format is 'Last, First [Suffix]' OR 'Last Suffix, First'
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            if len(parts) >= 2:
                last_part = parts[0]
                rest_parts = parts[1:]

                # check for suffix on the last part (e.g., 'Leal Jr.')
                last_tokens = last_part.split()
                suffix = ""
                if last_tokens and last_tokens[-1].rstrip('.').lower() in SUFFIX_MAP:
                    suffix = SUFFIX_MAP[last_tokens[-1].rstrip('.').lower()]
                    last_name = " ".join(last_tokens[:-1]) or last_tokens[0]
                else:
                    last_name = last_part

                # Build rest tokens while allowing a standalone suffix part (e.g., 'Leal, Jr., Noe')
                rest_tokens: List[str] = []
                for part in rest_parts:
                    t = part.strip()
                    if not t:
                        continue
                    if t.rstrip('.').lower() in SUFFIX_MAP:
                        suffix = SUFFIX_MAP[t.rstrip('.').lower()]
                        continue
                    rest_tokens.extend(t.split())

                # final check: trailing suffix token in rest_tokens (e.g., 'John Jr.')
                if rest_tokens and rest_tokens[-1].rstrip('.').lower() in SUFFIX_MAP:
                    suffix = SUFFIX_MAP[rest_tokens[-1].rstrip('.').lower()]
                    rest_tokens = rest_tokens[:-1]

                first_and_middle = " ".join(rest_tokens)
                name = (first_and_middle + " " + last_name).strip()
                if suffix:
                    name = f"{name} {suffix}"
                # Title-case each word (simple heuristic)
                return " ".join([w.capitalize() for w in name.split()])

        # No comma: assume 'First Last' or similar. Normalize whitespace and capitalization
        tokens = s.split()
        if not tokens:
            return ""
        # handle trailing suffix token
        suffix = ""
        if tokens and tokens[-1].rstrip('.').lower() in SUFFIX_MAP:
            suffix = SUFFIX_MAP[tokens[-1].rstrip('.').lower()]
            tokens = tokens[:-1]
        name = " ".join(tokens)
        if suffix:
            name = f"{name} {suffix}"
        return " ".join([w.capitalize() for w in name.split()])

    def process_guids(
        self,
        guids: List[str],
        save_csv: Optional[Path] = None,
        standings_lookup: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Process deck GUIDs and optionally enrich with standings data.
        
        Args:
            guids: List of deck GUIDs to fetch
            save_csv: Optional path to save combined CSV
            standings_lookup: Optional dict mapping player_name -> {wins, losses, draws, deck_archetype}
        """
        rows: List[Dict[str, Any]] = []
        for guid in guids:
            url = self.build_view_url(guid)
            payload = self.fetch_into_memory(url)
            if payload.get("status_code") != 200:
                print(f"Warning: {guid} returned {payload.get('status_code')}")
                continue
            card_rows = self.extract_cards_and_player(payload, guid)
            
            # Enrich with standings data if available
            if standings_lookup and card_rows:
                player_name = card_rows[0].get("player", "")
                player_data = standings_lookup.get(player_name, {})
                for row in card_rows:
                    row["wins"] = player_data.get("wins", "")
                    row["losses"] = player_data.get("losses", "")
                    row["draws"] = player_data.get("draws", "")
                    row["deck_archetype"] = player_data.get("deck_archetype", "")
            
            rows.extend(card_rows)

        if save_csv:
            save_csv.parent.mkdir(parents=True, exist_ok=True)
            with save_csv.open("w", encoding="utf-8", newline="") as fh:
                if rows:
                    fieldnames = ["player", "wins", "losses", "draws", "deck_archetype", "card_name", "qty", "zone", "deck_guid"]
                    writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)
            print("Saved combined CSV to", save_csv)

        return rows


if __name__ == "__main__":
    sample_guid = ["1cb305cb-c81e-4dce-ac4c-b32d00de6bcd", "09edec86-bc44-4ff1-95a7-b378004ea00d", "6a7ede40-da0c-4643-aa07-b37901544f86", "1133c3a9-32bb-4a16-9458-b37800b7b095"]

    def load_guids_from_standings(path: Path) -> List[str]:
        """Read a standings CSV and extract the `decklist_guid` column.

        Returns a deduped list preserving first-seen order. Non-empty strings only.
        """
        if not path.exists():
            return []
        guids: List[str] = []
        seen: Set[str] = set()
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = _csv.DictReader(fh)
                fieldnames = reader.fieldnames or []
                lower_fields = [f.lower() for f in fieldnames]
                if "decklist_guid" not in lower_fields:
                    print(f"Warning: 'decklist_guid' column not found in {path}")
                    return []
                for row in reader:
                    # handle case-insensitive header names
                    val = ""
                    for k, v in row.items():
                        if k and k.lower() == "decklist_guid":
                            val = (v or "").strip()
                            break
                    if not val:
                        continue
                    if val in seen:
                        continue
                    seen.add(val)
                    guids.append(val)
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return []
        return guids

    # prefer the latest standings file in data/ (allow EVENT_DATA_DIR override)
    data_dir = Path(os.environ.get("EVENT_DATA_DIR") or (Path(__file__).resolve().parents[1] / "data"))

    # 1) Prefer files that look like standings (contains 'standings') and are most recent
    standings_candidates = sorted(data_dir.glob("*standings*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    standings_path = None
    guids: List[str] = []

    def _try_load_from(path: Path) -> List[str]:
        try:
            vals = load_guids_from_standings(path)
            return vals
        except Exception:
            return []

    for cand in standings_candidates:
        vals = _try_load_from(cand)
        if vals:
            standings_path = cand
            guids = vals
            break

    # 2) If none of the 'standings' files contained guids, scan any CSVs in the folder
    if not guids:
        other_csvs = sorted(data_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        for cand in other_csvs:
            vals = _try_load_from(cand)
            if vals:
                standings_path = cand
                guids = vals
                break

    if standings_path:
        print(f"Loading GUIDs from: {standings_path}")
    else:
        print("No standings file with 'decklist_guid' found in data/; using sample GUIDs")
        guids = sample_guid

    # Build standings lookup: player_name -> {wins, losses, draws, deck_archetype}
    standings_lookup: Dict[str, Dict[str, Any]] = {}
    if standings_path and standings_path.exists():
        try:
            import pandas as pd
            import ast
            standings_df = pd.read_csv(standings_path, encoding="utf-8-sig")
            
            # Create a scraper instance to access normalize_player_name
            temp_scraper = DecklistScraper()
            
            for _, row in standings_df.iterrows():
                player_name_raw = str(row.get("PlayerName", "")).strip()
                if not player_name_raw:
                    continue
                
                # Normalize the player name to match what we'll get from decklists
                player_name = temp_scraper.normalize_player_name(player_name_raw)
                if not player_name:
                    continue
                
                # Parse MatchRecord (format: "W-L-D")
                match_record = str(row.get("MatchRecord", ""))
                wins, losses, draws = "", "", ""
                if match_record and "-" in match_record:
                    parts = match_record.split("-")
                    if len(parts) >= 3:
                        wins, losses, draws = parts[0], parts[1], parts[2]
                
                # Extract deck archetype from Decklists column (JSON/dict format)
                deck_archetype = ""
                decklists_data = str(row.get("Decklists", ""))
                if decklists_data and decklists_data != "nan":
                    try:
                        # Parse the list of decklists (usually just one)
                        decklist_list = ast.literal_eval(decklists_data)
                        if isinstance(decklist_list, list) and len(decklist_list) > 0:
                            # Get DecklistName from the first entry
                            deck_archetype = decklist_list[0].get("DecklistName", "").strip()
                    except (ValueError, SyntaxError, AttributeError):
                        pass
                
                standings_lookup[player_name] = {
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "deck_archetype": deck_archetype,
                }
            
            print(f"Loaded standings data for {len(standings_lookup)} players")
        except Exception as e:
            print(f"Warning: Failed to load standings data: {e}")
            standings_lookup = {}

    scraper = DecklistScraper()
    # include event name in decklist filename
    raw_event_name = os.environ.get("EVENT_NAME", "event")
    sanitized_event = re.sub(r'[<>:"/\\|?*]', '_', raw_event_name)
    out_path = data_dir / f"{sanitized_event} decklists.csv"
    start_ts = time.time()
    rows = scraper.process_guids(guids, save_csv=out_path, standings_lookup=standings_lookup)
    duration = time.time() - start_ts
    print("Parsed rows:", len(rows))

    # write a minimal completion log with timestamp and duration
    try:
        logs_dir = data_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        log_line = f"{now} | script=fetch_decklists_api | event={sanitized_event} | rows={len(rows)} | out={out_path} | duration_s={duration:.3f}"
        with (logs_dir / "fetch_decklists_api.log").open("a", encoding="utf-8") as fh:
            fh.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write decklists log: {e}")