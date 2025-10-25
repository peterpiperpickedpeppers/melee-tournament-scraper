# Melee Tournament Scraper

End-to-end pipeline to fetch Melee pairings, normalize per-archetype results, build matchup summaries, generate win-matrix visualizations, and compute per-card, per-copy winrates for every archetype.

## Quickstart

Install dependencies (prefer a virtual environment):

```bash
pip install -r requirements.txt
# optional: dev tools
pip install -r requirements-dev.txt
```

**Setup authentication:**

1. Copy `.env.example` to `.env`
2. Add your `MELEE_COOKIE` (see [Authentication](#authentication-and-cookies) below for how to get it)

That's it! The cookie is the only required config when using `main.py`.

**Run the full pipeline:**

```bash
python main.py --event-id 248718 --event-name "RC Houston 2025"
```

This runs all steps in order: fetch data → normalize → matchups → aggregate stats → win matrix → heatmap → per-card winrates.

Artifacts are written to `data/<EVENT_NAME>/`.

---

### Alternative: Run individual scripts

If you want to run scripts manually (e.g., for debugging), you'll need to set environment variables for EVENT_ID, EVENT_NAME, and EVENT_DATA_DIR in your `.env`:

```bash
# In .env (uncomment these only if running scripts individually)
# EVENT_ID=355905
# EVENT_NAME=PT EoE 2025
# EVENT_DATA_DIR=./data/PT EoE 2025
```

Then run each script:

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

# 5. Compute per-card, per-copy winrates (all archetypes)
python scripts/create_card_winrates.py
```

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
  - `create_card_winrates.py` – per-card, per-copy winrates for each archetype (writes to `card_winrates/`)
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
- Card winrates are written to `data/<EVENT_NAME>/card_winrates/` as one CSV per archetype, covering 0..N copies per card and location (main/side).

License: MIT
