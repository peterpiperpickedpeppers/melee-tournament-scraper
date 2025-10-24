import os
from pathlib import Path
import pandas as pd
import pytest


EVENT_DIR = os.getenv('EVENT_DATA_DIR')


def get_matchup_row(file: Path, opponent: str):
    df = pd.read_csv(file)
    row = df[df['Opponent_Archetype'] == opponent]
    if row.empty:
        return None
    r = row.iloc[0]
    return int(r['Wins']), int(r['Losses']), int(r['Draws']), int(r['Total_Matches'])


@pytest.mark.skipif(not EVENT_DIR, reason="EVENT_DATA_DIR not set")
def test_symmetry_esper_goryos_vs_azorius_blink():
    event_dir = Path(EVENT_DIR) # type: ignore
    mdir = event_dir / 'matchups'
    a_file = mdir / "Esper Goryo's matchups.csv"
    b_file = mdir / "Azorius Blink matchups.csv"

    if not a_file.exists() or not b_file.exists():
        pytest.skip("Matchup files not found")

    a_row = get_matchup_row(a_file, 'Azorius Blink')
    b_row = get_matchup_row(b_file, "Esper Goryo's")

    if a_row is None or b_row is None:
        pytest.skip("Specific matchup rows not found in files")
    assert a_row is not None and b_row is not None

    a_w, a_l, a_d, a_t = a_row
    b_w, b_l, b_d, b_t = b_row

    assert a_w == b_l
    assert a_l == b_w
    assert a_d == b_d
    assert a_t == a_w + a_l + a_d
    assert b_t == b_w + b_l + b_d
