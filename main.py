#!/usr/bin/env python
"""Orchestrator to run the three fetch scripts in order for a given event.

Usage:
    python main.py --event-id 12345 --event-name "My Event"

Behavior:
- Creates data/<event-name>/ with subfolders `matchups/` and `results/`.
- Runs, in order:
  1) scripts/fetch_standings_api.py
  2) scripts/fetch_pairings_api.py
  3) scripts/fetch_decklists_api.py
- Exports environment variables so the scripts write into the event folder.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
import sys
import time
from datetime import datetime


def run_script(python_exe: str, module_name: str, env: dict) -> int:
    """Run a module using `python -m module_name` so package imports resolve.

    Returns the subprocess return code.
    """
    print(f"Running module {module_name}...")
    cmd = [python_exe, "-m", module_name]
    proc = subprocess.run(cmd, env=env)
    return proc.returncode


def _append_log(log_path: Path, text: str) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except Exception:
        # Best effort only; don't fail the whole orchestrator for logging issues
        print(f"Unable to write log to {log_path}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run standings, pairings, and decklist fetchers for an event.")
    p.add_argument("--event-id", required=True, help="Event ID to use when fetching (numeric).")
    p.add_argument("--event-name", required=True, help="Event name (used to create data/<event-name>/ folder).")
    p.add_argument("--python", default=sys.executable, help="Python executable to run the scripts (default: current interpreter).")
    args = p.parse_args(argv)

    event_id = str(args.event_id)
    event_name = args.event_name
    python_exe = args.python

    repo_root = Path(__file__).resolve().parent
    data_root = repo_root / "data"
    event_dir = data_root / event_name
    matchups_dir = event_dir / "matchups"
    results_dir = event_dir / "results"

    # create folders
    matchups_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # prepare environment for subprocesses
    env = os.environ.copy()
    env["EVENT_ID"] = event_id
    env["EVENT_NAME"] = event_name
    env["EVENT_DATA_DIR"] = str(event_dir)

    # ensure event dir and logs dir exist
    event_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = event_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # script order: standings -> pairings -> decklists
    # We'll run them as modules (python -m scripts.fetch_standings_api) so imports like
    # `from utils.api_utils import ...` resolve from the repo root.
    modules = [
        "scripts.fetch_standings_api",
        "scripts.fetch_pairings_api",
        "scripts.fetch_decklists_api",
    ]

    for mod in modules:
        start_ts = time.time()
        rc = run_script(python_exe, mod, env)
        end_ts = time.time()
        duration = end_ts - start_ts
        now = datetime.utcnow().isoformat() + "Z"
        log_line = f"{now} | module={mod} | rc={rc} | duration_s={duration:.3f}"
        _append_log(logs_dir / "main.log", log_line)
        print(log_line)
        if rc != 0:
            print(f"Module {mod} exited with code {rc}. Aborting.")
            return rc

    print("All scripts completed successfully. Artifacts are in:", event_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
