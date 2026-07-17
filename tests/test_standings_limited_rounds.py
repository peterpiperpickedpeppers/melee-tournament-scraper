import pandas as pd

from scripts.fetch_decklists_api import build_standings_lookup_from_path
from scripts.fetch_standings_api import _is_limited_round_row


def test_limited_round_detection_for_pt_like_events():
    row = pd.Series({
        "RoundNumber": 2,
        "PhaseName": "Swiss",
        "Round": "Round 2",
    })

    assert _is_limited_round_row(row, event_name="PT Marvel 2026", limited_round_count=3) is True


def test_build_standings_lookup_prefers_constructed_totals_from_summary(tmp_path):
    summary_path = tmp_path / "PT Test standings summary.csv"
    summary_path.write_text(
        "PlayerName,constructed_wins,constructed_losses,constructed_draws,decklist_guid\n"
        "Alice,10,2,1,GUID123\n",
        encoding="utf-8-sig",
    )

    lookup = build_standings_lookup_from_path(summary_path)

    assert lookup["Alice"]["wins"] == "10"
    assert lookup["Alice"]["losses"] == "2"
    assert lookup["Alice"]["draws"] == "1"
