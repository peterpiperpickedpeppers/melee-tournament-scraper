import os
from pathlib import Path
import pandas as pd
import pytest


EVENT_DIR = os.getenv('EVENT_DATA_DIR')


@pytest.mark.skipif(not EVENT_DIR, reason="EVENT_DATA_DIR not set")
def test_no_mirror_rows_in_matchups():
    event_dir = Path(EVENT_DIR) # type: ignore
    mdir = event_dir / 'matchups'
    if not mdir.exists():
        pytest.skip('Matchups dir not found')

    for f in mdir.glob('* matchups.csv'):
        archetype = f.stem.replace(' matchups', '')
        df = pd.read_csv(f)
        # Opponent_Archetype should never equal the file archetype (mirrors excluded)
        assert not (df['Opponent_Archetype'] == archetype).any(), f"Mirror row found in {f.name}"
