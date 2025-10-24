# Melee Tournament Scraper

End-to-end pipeline to fetch Melee pairings, normalize per-archetype results, build matchup summaries, and generate win-matrix visualizations.

## Quickstart

Install dependencies (prefer a virtual environment):

```bash
pip install -r requirements.txt
# optional: dev tools
pip install -r requirements-dev.txt
```

1. Create a `.env` from `.env.example` and fill in values (MELEE_COOKIE required to fetch):

- EVENT_ID: Melee event ID
- EVENT_NAME: Human-friendly name used in output filenames
- EVENT_DATA_DIR: Directory under `data/` for event artifacts
- MELEE_COOKIE: Cookie string from your logged-in browser session

2. Run the full pipeline

**Option A: Use the orchestrator (recommended)**

```bash
python main.py --event-id 355905 --event-name "PT EoE 2025"
```

This runs all steps in order: fetch data → normalize → matchups → aggregate stats → win matrix → heatmap.

**Option B: Run individual scripts**

```bash
# 1. Fetch data (requires MELEE_COOKIE)
python scripts/fetch_standings_api.py
python scripts/fetch_pairings_api.py
python scripts/fetch_decklists_api.py

# 2. Create per-archetype results
python scripts/filter_pairings_by_archetype.py

# 3. Create matchup files
python scripts/create_matchups_files.py

# 4. Generate summaries and visualizations
python scripts/create_aggregate_stats.py
python scripts/create_win_matrix.py
python scripts/create_win_matrix_heatmap.py
```

**Option C: VS Code tasks**

Or in VS Code: open the Command Palette and run "Tasks: Run Task" to choose:

- Fetch pairings
- Filter results by archetype
- Create matchups
- Aggregate stats
- Win matrix CSV
- Win matrix heatmap
- Run full pipeline

Artifacts are written under `data/<EVENT_NAME>/`.

## Repository structure

- `main.py` – orchestrator to run the full pipeline with one command
- `scripts/` – user-facing pipeline and utilities
  - `fetch_standings_api.py` – fetch standings data from Melee
  - `fetch_pairings_api.py` – fetch and clean pairings from Melee
  - `fetch_decklists_api.py` – fetch decklists for all players
  - `filter_pairings_by_archetype.py` – normalize results (player deck always on the left)
  - `create_matchups_files.py` – aggregate per-archetype matchup summaries (mirrors excluded)
  - `create_aggregate_stats.py` – overall W/L/D per archetype (no mirrors)
  - `create_win_matrix.py` – CSV win matrix for top-N archetypes
  - `create_win_matrix_heatmap.py` – annotated heatmap visualization
  - `verify_matchup.py` – CLI to verify head-to-head symmetry and counts
- `tools/` – maintainer-only diagnostic scripts (not required for end users)
- `utils/` – API helpers and data utilities
- `tests/` – lightweight correctness checks (run with `pytest`)

## Developer tools

We keep ad hoc helper scripts under `tools/` so the public runtime stays lean. Useful checks have been promoted to either a CLI (`scripts/verify_matchup.py`) or to tests under `tests/`.

Verify a specific head-to-head anywhere:

```bash
python scripts/verify_matchup.py --deck-a "Azorius Blink" --deck-b "Esper Goryo's" --event-dir "data/RC Houston 2025"
```

## Tests

Install dev deps and run:

```bash
pip install pytest
pytest -q
```

Tests are designed to skip gracefully if local data files aren’t present.

## Authentication and cookies

- Never commit MELEE_COOKIE. Keep it only in your local `.env` (this repo’s `.gitignore` already ignores `.env`, `data/`, and `logs/`).
- Cookies can appear long‑lived but may be invalidated at any time (logout, server rotation, IP change, etc.). Treat them as ephemeral.
- If fetching fails (401/403) or returns no rounds, first refresh the cookie.

How to refresh MELEE_COOKIE:

1. Log in to the site in your browser.
2. Open Developer Tools → Network tab.
3. Trigger a page/request related to the event, click the network entry, and find the Request Headers → Cookie value.
4. Copy the full cookie string and update your local `.env`:

```
MELEE_COOKIE="<paste cookie here>"
```

On Windows, you can also set it as a user environment variable so it persists across shells:

```cmd
setx MELEE_COOKIE "<paste cookie here>"
```

In CI, pass MELEE_COOKIE via repository secrets; do not hardcode or commit it.

## Notes

- Mirror matches are intentionally excluded from matchup summaries.
- Decklist and player names are stripped at fetch time to avoid whitespace bugs.

License: MIT
