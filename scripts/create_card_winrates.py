#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Create per-card, per-copy winrate CSVs for every archetype.

Reads the event decklists CSV, computes winrates by copy count for each
unique deck_archetype (including pilots who played 0 copies of a card),
and writes outputs to data/<EVENT_NAME>/card_winrates/.

The HTML report layer can optionally hide rows where # of Pilots is 0 to
reduce clutter, while leaving the CSV output exhaustive.

Requires: EVENT_DATA_DIR and EVENT_NAME in the environment (set by main.py),
and an existing decklists CSV named "<EVENT_NAME> decklists.csv" in EVENT_DATA_DIR.
"""

import os
import sys
import re
import requests
import webbrowser
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Set
import pandas as pd

# Ensure repository root is on sys.path for local imports when executed directly
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fetch_decklists_api import DecklistScraper
from utils.api_utils import parse_result_string
from utils.api_utils import classify_event_round_ids
from scripts.card_winrates_per_archetype import archetype_card_copy_winrates


def _is_valid_match_row(row: pd.Series) -> bool:
    """Return True for rows that should count toward card winrates."""
    outcome = str(row.get("Outcome", "") or "")
    result_string = str(row.get("ResultString", "") or "")

    if not outcome and not result_string:
        return False

    if outcome.strip().lower() == "bye":
        return False

    if "0-0-3" in result_string:
        return False

    if "draw" in outcome.lower() or "draw" in result_string.lower():
        return False

    return True


def build_pilot_result_lookup_from_pairings(
    pairings_df: pd.DataFrame,
    pilots: Optional[List[str]] = None,
    constructed_pilots: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, int]]:
    """Build pilot -> {Wins, Losses} from constructed-only pairings rows."""
    if pilots is None:
        pilots = []

    normalizer = DecklistScraper().normalize_player_name
    lookup: Dict[str, Dict[str, int]] = {
        normalizer(str(pilot).strip()): {"Wins": 0, "Losses": 0}
        for pilot in pilots
        if str(pilot).strip()
    }
    if pairings_df.empty:
        return lookup

    if constructed_pilots is None:
        constructed_pilots = set(lookup.keys())
    else:
        constructed_pilots = {normalizer(str(p).strip()) for p in constructed_pilots if str(p).strip()}

    for _, row in pairings_df.iterrows():
        if not _is_valid_match_row(row):
            continue

        player = normalizer(str(row.get("Player") or ""))
        opponent = normalizer(str(row.get("Opponent") or ""))
        result_string = str(row.get("ResultString") or "")
        outcome = str(row.get("Outcome") or "")

        if not player and not opponent:
            continue

        if player not in constructed_pilots or opponent not in constructed_pilots:
            continue

        winner_name, is_draw, is_bye = parse_result_string(result_string or outcome)
        if is_draw or is_bye or not winner_name:
            continue

        winner_key = normalizer(winner_name)
        if winner_key == player:
            if opponent in lookup:
                lookup[opponent]["Losses"] += 1
            if player in lookup:
                lookup[player]["Wins"] += 1
        elif winner_key == opponent:
            if player in lookup:
                lookup[player]["Losses"] += 1
            if opponent in lookup:
                lookup[opponent]["Wins"] += 1

    return lookup


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', str(name))


def _parse_round_id_env(raw: str) -> Set[int]:
    vals: Set[int] = set()
    if not raw:
        return vals
    for token in re.split(r"[,\s]+", raw.strip()):
        if not token:
            continue
        try:
            vals.add(int(token))
        except ValueError:
            continue
    return vals


def _env_flag(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
                return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_slug(name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", str(name)).strip("-")
        return cleaned.lower() or "archetype"


def _to_html_table(df: pd.DataFrame) -> str:
        html_df = df.copy()
        if "Win%" in html_df.columns:
                html_df["Win%"] = pd.to_numeric(html_df["Win%"], errors="coerce").fillna(0).map(lambda x: f"{x:.2f}%")

        for col in ["Copies", "# of Pilots", "Wins", "Losses"]:
                if col in html_df.columns:
                        html_df[col] = pd.to_numeric(html_df[col], errors="coerce").fillna(0).astype(int)

        return html_df.to_html(index=False, classes="winrate-table", border=0, escape=True)


def _filter_zero_pilot_rows_for_html(df: pd.DataFrame) -> pd.DataFrame:
    if "# of Pilots" not in df.columns:
        return df

    pilot_counts = pd.to_numeric(df["# of Pilots"], errors="coerce").fillna(0)
    return df.loc[pilot_counts > 0].reset_index(drop=True)


def _build_archetype_html(event_name: str, archetype: str, table_html: str, generated_at: str) -> str:
        return f"""<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{escape(event_name)} - {escape(archetype)} Card Winrates</title>
    <style>
        :root {{
            --bg: #f7faf8;
            --panel: #ffffff;
            --ink: #1f2a2e;
            --muted: #5f6f75;
            --line: #dde6e2;
        }}
        body {{
            margin: 0;
            font-family: Segoe UI, Arial, sans-serif;
            color: var(--ink);
            background: linear-gradient(180deg, #ecf4ef 0%, var(--bg) 45%);
        }}
        .wrap {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}
        .card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 14px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
            overflow: hidden;
        }}
        .header {{
            padding: 18px 20px;
            border-bottom: 1px solid var(--line);
            background: #f4faf6;
        }}
        h1 {{ margin: 0; font-size: 22px; }}
        .meta {{ color: var(--muted); margin-top: 6px; font-size: 13px; }}
        .toolbar {{
            padding: 12px 20px;
            border-bottom: 1px solid var(--line);
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        input[type=\"search\"] {{
            width: min(420px, 100%);
            padding: 8px 10px;
            border: 1px solid #cdd8d2;
            border-radius: 8px;
            font-size: 14px;
        }}
        .table-wrap {{ overflow: auto; max-height: 78vh; }}
        table.winrate-table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
        table.winrate-table thead th {{
            position: sticky;
            top: 0;
            z-index: 2;
            background: #eef5f2;
            border-bottom: 1px solid #cfdcd6;
            padding: 10px;
            text-align: left;
            cursor: pointer;
            white-space: nowrap;
        }}
        table.winrate-table td {{ border-bottom: 1px solid #edf2ef; padding: 9px 10px; }}
        table.winrate-table tbody tr:nth-child(even) {{ background: #fbfdfc; }}
        table.winrate-table td:nth-child(n+4),
        table.winrate-table th:nth-child(n+4) {{ text-align: right; }}
        .footer {{ padding: 12px 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }}
        a {{ color: #1e6b59; text-decoration: none; }}
    </style>
</head>
<body>
    <div class=\"wrap\">
        <div class=\"card\">
            <div class=\"header\">
                <h1>{escape(archetype)} Card Winrates by Copy Count</h1>
                <div class=\"meta\">Event: {escape(event_name)} | Generated: {escape(generated_at)}</div>
            </div>
            <div class=\"toolbar\">
                <a href=\"index.html\">Back to index</a>
                <input id=\"tableSearch\" type=\"search\" placeholder=\"Filter rows (card name, loc, copies, etc.)\" />
            </div>
            <div class=\"table-wrap\">{table_html}</div>
            <div class=\"footer\">Tip: click column headers to sort.</div>
        </div>
    </div>
    <script>
        const table = document.querySelector('table.winrate-table');
        const rows = Array.from(table.tBodies[0].rows);
        const search = document.getElementById('tableSearch');

        search.addEventListener('input', () => {{
            const q = search.value.toLowerCase().trim();
            for (const r of rows) {{
                r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
            }}
        }});

        function toSortValue(text) {{
            const cleaned = text.replace('%', '').replace(/,/g, '').trim();
            const n = Number(cleaned);
            return Number.isNaN(n) ? text.toLowerCase() : n;
        }}

        Array.from(table.tHead.rows[0].cells).forEach((th, idx) => {{
            let asc = true;
            th.addEventListener('click', () => {{
                rows.sort((a, b) => {{
                    const av = toSortValue(a.cells[idx]?.textContent || '');
                    const bv = toSortValue(b.cells[idx]?.textContent || '');
                    if (av < bv) return asc ? -1 : 1;
                    if (av > bv) return asc ? 1 : -1;
                    return 0;
                }});
                asc = !asc;
                for (const r of rows) table.tBodies[0].appendChild(r);
            }});
        }});

        const pctColIndex = Array.from(table.tHead.rows[0].cells).findIndex(
            (c) => c.textContent.trim() === 'Win%'
        );
        if (pctColIndex >= 0) {{
            for (const r of rows) {{
                const cell = r.cells[pctColIndex];
                const v = Number((cell.textContent || '').replace('%', '').trim());
                if (!Number.isNaN(v)) {{
                    const hue = Math.max(0, Math.min(120, v * 1.2));
                    cell.style.backgroundColor = `hsl(${{hue}} 70% 88%)`;
                    cell.style.fontWeight = '600';
                }}
            }}
        }}
    </script>
</body>
</html>
"""


def _build_index_html(event_name: str, generated_at: str, rows: List[Dict[str, str]]) -> str:
        body_rows = "\n".join(
                f"<tr><td><a href=\"{escape(r['file'])}\">{escape(r['archetype'])}</a></td><td>{escape(r['rows'])}</td></tr>"
                for r in rows
        )
        return f"""<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{escape(event_name)} - Card Winrates Report</title>
    <style>
        body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; color: #1f2a2e; background: #f4f8f6; }}
        .wrap {{ max-width: 980px; margin: 0 auto; padding: 24px; }}
        .card {{ background: #fff; border: 1px solid #dfe8e3; border-radius: 14px; overflow: hidden; }}
        .head {{ padding: 18px 20px; background: #eef6f2; border-bottom: 1px solid #dfe8e3; }}
        h1 {{ margin: 0; font-size: 24px; }}
        .meta {{ margin-top: 6px; color: #5f6f75; font-size: 13px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px 12px; border-bottom: 1px solid #eef3f0; text-align: left; }}
        th {{ background: #f8fbf9; }}
        tbody tr:nth-child(even) {{ background: #fbfdfc; }}
        a {{ color: #1e6b59; text-decoration: none; font-weight: 600; }}
    </style>
</head>
<body>
    <div class=\"wrap\">
        <div class=\"card\">
            <div class=\"head\">
                <h1>Card Winrates HTML Report</h1>
                <div class=\"meta\">Event: {escape(event_name)} | Generated: {escape(generated_at)} | Archetypes: {len(rows)}</div>
            </div>
            <table>
                <thead>
                    <tr><th>Archetype</th><th>Rows</th></tr>
                </thead>
                <tbody>
                    {body_rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


def _write_card_winrate_html_reports(
        event_name: str,
        html_dir: Path,
        tables_by_archetype: Dict[str, pd.DataFrame],
) -> Optional[Path]:
        html_dir.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        index_rows: List[Dict[str, str]] = []
        for archetype, tbl in sorted(tables_by_archetype.items(), key=lambda x: x[0].lower()):
                slug = _sanitize_slug(archetype)
                filename = f"{slug}.html"
                out_path = html_dir / filename
                table_html = _to_html_table(tbl)
                page_html = _build_archetype_html(event_name, archetype, table_html, generated_at)
                out_path.write_text(page_html, encoding="utf-8")
                index_rows.append({"archetype": archetype, "rows": str(len(tbl)), "file": filename})

        index_html = _build_index_html(event_name, generated_at, index_rows)
        index_path = html_dir / "index.html"
        index_path.write_text(index_html, encoding="utf-8")
        return index_path


def _get_constructed_round_ids_from_standings_files(event_path: Path) -> Set[int]:
    round_ids: Set[int] = set()
    for p in event_path.glob("*standings round_*.csv"):
        m = re.search(r"round_(\d+)\.csv$", p.name)
        if m:
            round_ids.add(int(m.group(1)))
    return round_ids


def _get_constructed_round_ids_from_file(event_path: Path) -> Set[int]:
    ids_file = event_path / "constructed_round_ids.txt"
    if not ids_file.exists():
        return set()
    try:
        return _parse_round_id_env(ids_file.read_text(encoding="utf-8"))
    except Exception:
        return set()


def create_all_card_winrates(min_pilots: int = 0, max_copies_cap: Optional[int] = 4) -> List[Path]:
    event_dir = os.getenv('EVENT_DATA_DIR')
    event_name = os.getenv('EVENT_NAME', 'event')
    event_dir = event_dir.strip() if event_dir else event_dir
    event_name = event_name.strip() if event_name else event_name
    if not event_dir:
        raise ValueError('EVENT_DATA_DIR environment variable not set')

    event_path = Path(event_dir)
    decklists_csv = event_path / f"{event_name} decklists.csv"
    if not decklists_csv.exists():
        raise FileNotFoundError(f"Decklists file not found: {decklists_csv}")

    out_dir = event_path / 'card_winrates'
    out_dir.mkdir(parents=True, exist_ok=True)
    html_enabled = _env_flag("CARD_WINRATES_HTML", True)
    hide_zero_pilot_rows = _env_flag("CARD_WINRATES_HIDE_ZERO_PILOT_ROWS", True)
    open_html = _env_flag("CARD_WINRATES_OPEN_HTML", False)
    html_dir = event_path / 'card_winrates_html'

    df = pd.read_csv(decklists_csv)
    # Ensure expected columns present for the helper
    # helper will rename: player->pilot, card_name->card, qty->Copies, zone->loc, wins/losses

    # Drop rows with missing archetype
    df = df.dropna(subset=['deck_archetype']).copy()

    pairings_csv = event_path / f"{event_name} pairings.csv"
    normalizer = DecklistScraper().normalize_player_name
    pilot_results_lookup: Dict[str, Dict[str, int]] = {}
    if pairings_csv.exists():
        pairings_df = pd.read_csv(pairings_csv)

        # Round filtering precedence:
        # 1) CONSTRUCTED_ROUND_IDS env (explicit allow-list)
        # 2) standings round files in event dir (best-effort constructed proxy)
        # 3) no round filter
        explicit_constructed = _parse_round_id_env(os.getenv("CONSTRUCTED_ROUND_IDS", ""))
        file_constructed = _get_constructed_round_ids_from_file(event_path)
        standings_round_ids = _get_constructed_round_ids_from_standings_files(event_path)

        include_round_ids: Set[int] = set()
        event_type = (os.getenv("EVENT_TYPE") or "constructed").strip().lower()
        event_id_raw = (os.getenv("EVENT_ID") or "").strip()
        if event_id_raw.isdigit():
            try:
                classified = classify_event_round_ids(requests.Session(), int(event_id_raw), event_type, mode="pairings")
                include_round_ids = set(int(x) for x in classified.get("constructed_ids", []))
                limited_round_ids = sorted(int(x) for x in classified.get("limited_ids", []))
                if limited_round_ids:
                    print(f"Detected limited rounds from event type ({event_type}): {limited_round_ids}")
            except Exception as exc:
                print(f"Warning: failed to classify rounds from event metadata: {exc}")

        if not include_round_ids:
            include_round_ids = explicit_constructed or file_constructed or standings_round_ids

        if include_round_ids and "RoundId" in pairings_df.columns:
            before = len(pairings_df)
            pairings_df = pairings_df[pd.to_numeric(pairings_df["RoundId"], errors="coerce").isin(include_round_ids)].copy()
            after = len(pairings_df)
            print(
                f"Filtering pairings to constructed rounds: {sorted(include_round_ids)} "
                f"({before} -> {after} rows)"
            )
        else:
            print("No constructed round filter found; using all pairings rounds.")

        constructed_pilots = {
            normalizer(str(p).strip())
            for p in df['player'].dropna().astype(str).str.strip().unique().tolist()
            if str(p).strip()
        }
        pilot_results_lookup = build_pilot_result_lookup_from_pairings(
            pairings_df,
            pilots=sorted(constructed_pilots),
            constructed_pilots=constructed_pilots,
        )
    else:
        print(f"Pairings CSV not found at {pairings_csv}; falling back to standings-derived wins/losses")

    # Keep canonical lowercase columns and let the helper normalize names.
    # This avoids creating duplicate "Wins"/"Losses" columns via renaming.
    if pilot_results_lookup:
        df["wins"] = df["player"].map(lambda p: pilot_results_lookup.get(normalizer(str(p).strip()), {}).get("Wins", 0))
        df["losses"] = df["player"].map(lambda p: pilot_results_lookup.get(normalizer(str(p).strip()), {}).get("Losses", 0))
    else:
        df["wins"] = pd.to_numeric(df["wins"], errors="coerce").fillna(0).astype(int)
        df["losses"] = pd.to_numeric(df["losses"], errors="coerce").fillna(0).astype(int)

    archetypes = sorted(df['deck_archetype'].dropna().unique().tolist())
    print(f"Found {len(archetypes)} unique archetypes in decklists")

    written_files: List[Path] = []
    tables_by_archetype: Dict[str, pd.DataFrame] = {}
    for archetype in archetypes:
        try:
            tbl = archetype_card_copy_winrates(
                df,
                archetype=archetype,
                loc=None,
                min_pilots=min_pilots,
                max_copies_cap=max_copies_cap,
            )
        except Exception as e:
            print(f"Error computing card winrates for {archetype}: {e}")
            continue

        safe_name = _sanitize_filename(archetype)
        out_csv = out_dir / f"{safe_name} per card per copy winrates.csv"
        tbl.to_csv(out_csv, index=False, encoding='utf-8')
        written_files.append(out_csv)
        if html_enabled:
            html_tbl = _filter_zero_pilot_rows_for_html(tbl) if hide_zero_pilot_rows else tbl.copy()
            tables_by_archetype[archetype] = html_tbl
        print(f"Wrote {len(tbl)} rows -> {out_csv}")

    if html_enabled and tables_by_archetype:
        index_path = _write_card_winrate_html_reports(event_name, html_dir, tables_by_archetype)
        if index_path is not None:
            print(f"Wrote HTML report index -> {index_path}")
            if open_html:
                try:
                    webbrowser.open(index_path.resolve().as_uri())
                except Exception as exc:
                    print(f"Warning: unable to open HTML report in browser: {exc}")

    print(f"Completed card winrates for {len(written_files)}/{len(archetypes)} archetypes.")
    return written_files


if __name__ == '__main__':
    written = create_all_card_winrates()
    if not written:
        raise SystemExit("No card winrate files were generated.")
