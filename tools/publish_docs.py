#!/usr/bin/env python

"""Publish tournament reports and heatmaps into docs/ for GitHub Pages.

Usage:
    python tools/publish_docs.py [--event EVENT_NAME] [--data-root PATH] [--docs-root PATH]

Flags:
    --event       Publish only the named tournament. Repeat to publish several.
    --data-root   Root data directory that contains event folders. Defaults to data/.
    --docs-root   Output folder for the GitHub Pages site. Defaults to docs/.

Default behavior: rebuild the published site for every publishable tournament
found under data/.

Selective behavior: pass one or more --event arguments to refresh only the
named tournaments while keeping the rest of docs/ intact.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Sequence
from urllib.parse import quote


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
DEFAULT_DOCS_ROOT = REPO_ROOT / "docs"


@dataclass(frozen=True)
class TournamentRecord:
    event_name: str
    slug: str
    source_dir: Path
    published_at: str
    card_winrates_index: str
    heatmaps: list[str]


def _sanitize_slug(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", str(name)).strip("-")
    return cleaned.lower() or "event"


def _url(path: str) -> str:
    return quote(path.replace("\\", "/"))


def _sorted_heatmaps(event_dir: Path) -> list[Path]:
    heatmaps = [p for p in event_dir.glob("*win matrix heatmap*.png") if p.is_file()]
    return sorted(heatmaps, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)


def _has_publishable_assets(event_dir: Path) -> bool:
    html_index = event_dir / "card_winrates_html" / "index.html"
    return html_index.exists() and bool(_sorted_heatmaps(event_dir))


def _discover_event_dirs(data_root: Path) -> list[Path]:
    candidates: list[Path] = []
    if not data_root.exists():
        return candidates

    for child in data_root.iterdir():
        if not child.is_dir():
            continue
        if _has_publishable_assets(child):
            candidates.append(child)

    return sorted(candidates, key=lambda p: p.name.lower())


def _resolve_requested_event_dirs(data_root: Path, event_names: Sequence[str]) -> list[Path]:
    requested: list[Path] = []
    seen: set[str] = set()
    for raw_name in event_names:
        event_name = str(raw_name).strip()
        if not event_name or event_name in seen:
            continue
        seen.add(event_name)
        event_dir = data_root / event_name
        if not event_dir.exists() or not event_dir.is_dir():
            raise FileNotFoundError(f"Event directory not found: {event_dir}")
        if not _has_publishable_assets(event_dir):
            raise FileNotFoundError(
                f"Event '{event_name}' is missing publishable assets in {event_dir}. "
                "Expected card_winrates_html/index.html and at least one heatmap PNG."
            )
        requested.append(event_dir)
    return requested


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _build_tournament_page(record: TournamentRecord) -> str:
    if record.heatmaps:
        heatmap_items = "\n".join(
            f'<li><a href="{_url(path)}">{escape(Path(path).name)}</a></li>'
            for path in record.heatmaps
        )
        primary_heatmap = record.heatmaps[0]
        heatmap_block = f"""
            <div class="heatmap-view">
                <img src="{_url(primary_heatmap)}" alt="{escape(record.event_name)} heatmap" />
            </div>
            <div class="asset-list">
                <h2>Heatmap Files</h2>
                <ul>
                    {heatmap_items}
                </ul>
            </div>
        """
    else:
        heatmap_block = "<p>No heatmap image was published for this tournament.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(record.event_name)} Tournament Report</title>
    <style>
        :root {{
            --bg: #f5f8f6;
            --panel: #ffffff;
            --ink: #1f2a2e;
            --muted: #5f6f75;
            --line: #dfe8e3;
            --accent: #1e6b59;
        }}
        body {{
            margin: 0;
            font-family: Segoe UI, Arial, sans-serif;
            color: var(--ink);
            background: linear-gradient(180deg, #edf5f0 0%, var(--bg) 42%);
        }}
        .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
        .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06); }}
        .head {{ padding: 20px 22px; border-bottom: 1px solid var(--line); background: #f4faf7; }}
        h1 {{ margin: 0; font-size: 24px; }}
        .meta {{ margin-top: 6px; color: var(--muted); font-size: 13px; }}
        .toolbar {{ padding: 14px 22px; border-bottom: 1px solid var(--line); display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
        .button {{ display: inline-block; padding: 9px 14px; border-radius: 999px; background: var(--accent); color: #fff; text-decoration: none; font-weight: 600; }}
        .button.secondary {{ background: #eef4f1; color: var(--accent); }}
        .content {{ padding: 22px; }}
        .panel {{ margin-bottom: 22px; padding: 18px; border: 1px solid var(--line); border-radius: 14px; background: #fbfdfc; }}
        .panel h2 {{ margin: 0 0 10px 0; font-size: 18px; }}
        .heatmap-view {{ overflow: auto; border: 1px solid var(--line); border-radius: 12px; background: #fff; padding: 10px; }}
        .heatmap-view img {{ display: block; max-width: 100%; height: auto; }}
        .asset-list ul {{ margin: 0; padding-left: 20px; }}
        .asset-list li {{ margin: 6px 0; }}
        a {{ color: var(--accent); }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="card">
            <div class="head">
                <h1>{escape(record.event_name)}</h1>
                <div class="meta">Published: {escape(record.published_at)} | Slug: {escape(record.slug)}</div>
            </div>
            <div class="toolbar">
                <a class="button secondary" href="../index.html">Back to tournament index</a>
            </div>
            <div class="content">
                <div class="panel">
                    <h2>Card Winrates</h2>
                    <p><a href="{_url(record.card_winrates_index)}">Open the card-winrate report index</a>.</p>
                </div>
                <div class="panel">
                    <h2>Heatmap</h2>
                    {heatmap_block}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def _build_root_index(records: Sequence[TournamentRecord]) -> str:
    rows = []
    for record in records:
        event_page_link = _url(f"{record.slug}/index.html")
        rows.append(
            "<tr>"
            f'<td><a href="{event_page_link}">{escape(record.event_name)}</a></td>'
            f"<td>{escape(record.published_at)}</td>"
            "</tr>"
        )

    body_rows = "\n".join(rows) if rows else "<tr><td colspan=2>No tournaments have been published yet.</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Tournament Pages</title>
    <style>
        :root {{
            --bg: #f5f8f6;
            --panel: #ffffff;
            --ink: #1f2a2e;
            --muted: #5f6f75;
            --line: #dfe8e3;
            --accent: #1e6b59;
        }}
        body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; color: var(--ink); background: linear-gradient(180deg, #edf5f0 0%, var(--bg) 42%); }}
        .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
        .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06); }}
        .head {{ padding: 20px 22px; border-bottom: 1px solid var(--line); background: #f4faf7; }}
        h1 {{ margin: 0; font-size: 24px; }}
        .meta {{ margin-top: 6px; color: var(--muted); font-size: 13px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px 14px; border-bottom: 1px solid #eef3f0; text-align: left; vertical-align: top; }}
        th {{ background: #fafdfb; font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }}
        tbody tr:nth-child(even) {{ background: #fbfdfc; }}
        a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="card">
            <div class="head">
                <h1>Tournament Pages</h1>
                <div class="meta">Click a tournament to open its landing page, then jump into the card-winrate report or heatmap.</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Tournament</th>
                        <th>Published</th>
                    </tr>
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


def _load_published_records(docs_root: Path) -> list[TournamentRecord]:
    records: list[TournamentRecord] = []
    if not docs_root.exists():
        return records

    for meta_path in sorted(docs_root.glob("*/published.json")):
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            records.append(
                TournamentRecord(
                    event_name=str(payload["event_name"]),
                    slug=str(payload["slug"]),
                    source_dir=Path(str(payload["source_dir"])),
                    published_at=str(payload["published_at"]),
                    card_winrates_index=str(payload["card_winrates_index"]),
                    heatmaps=[str(item) for item in payload.get("heatmaps", [])],
                )
            )
        except Exception:
            continue

    return sorted(records, key=lambda record: record.event_name.lower())


def _publish_event(event_dir: Path, docs_root: Path) -> TournamentRecord:
    event_name = event_dir.name
    slug = _sanitize_slug(event_name)
    target_dir = docs_root / slug
    html_src = event_dir / "card_winrates_html"
    html_dst = target_dir / "card_winrates_html"
    heatmap_srcs = _sorted_heatmaps(event_dir)
    heatmap_dst = target_dir / "heatmaps"

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    _copy_tree(html_src, html_dst)
    heatmap_dst.mkdir(parents=True, exist_ok=True)
    for heatmap_src in heatmap_srcs:
        shutil.copy2(heatmap_src, heatmap_dst / heatmap_src.name)

    published_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    record = TournamentRecord(
        event_name=event_name,
        slug=slug,
        source_dir=event_dir,
        published_at=published_at,
        card_winrates_index="card_winrates_html/index.html",
        heatmaps=[f"heatmaps/{heatmap_src.name}" for heatmap_src in heatmap_srcs],
    )

    (target_dir / "index.html").write_text(_build_tournament_page(record), encoding="utf-8")
    (target_dir / "published.json").write_text(
        json.dumps(
            {
                "event_name": record.event_name,
                "slug": record.slug,
                "source_dir": str(record.source_dir),
                "published_at": record.published_at,
                "card_winrates_index": record.card_winrates_index,
                "heatmaps": record.heatmaps,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return record


def publish_docs(
    event_names: Sequence[str] | None = None,
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    docs_root: Path = DEFAULT_DOCS_ROOT,
) -> list[Path]:
    if event_names:
        event_dirs = _resolve_requested_event_dirs(data_root, event_names)
        docs_root.mkdir(parents=True, exist_ok=True)
    else:
        event_dirs = _discover_event_dirs(data_root)
        if docs_root.exists():
            shutil.rmtree(docs_root)
        docs_root.mkdir(parents=True, exist_ok=True)

    published_records: list[TournamentRecord] = []
    for event_dir in event_dirs:
        published_records.append(_publish_event(event_dir, docs_root))

    root_records = _load_published_records(docs_root) if event_names else published_records
    (docs_root / "index.html").write_text(_build_root_index(root_records), encoding="utf-8")

    return [docs_root / record.slug for record in root_records]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish tournament HTML reports into docs/ for GitHub Pages.")
    parser.add_argument(
        "--event",
        action="append",
        dest="events",
        help="Publish only the named tournament. Repeat the flag to publish several tournaments.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root data directory that contains event folders.",
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=DEFAULT_DOCS_ROOT,
        help="Output folder for the GitHub Pages site.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    publish_docs(args.events, data_root=args.data_root, docs_root=args.docs_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())