import pandas as pd

from scripts.create_card_winrates import build_pilot_result_lookup_from_pairings


def test_build_pilot_result_lookup_excludes_draws_byes_and_incomplete_matches():
    pairings = pd.DataFrame(
        [
            {
                "Player": "Alice",
                "Opponent": "Bob",
                "Outcome": "Alice won",
                "ResultString": "Alice won 2-0-0",
            },
            {
                "Player": "Alice",
                "Opponent": "Carol",
                "Outcome": "Draw",
                "ResultString": "1-1-0 Draw",
            },
            {
                "Player": "Alice",
                "Opponent": "Dana",
                "Outcome": "Bye",
                "ResultString": "Alice was assigned a bye",
            },
            {
                "Player": "Alice",
                "Opponent": "Eve",
                "Outcome": "Eve won",
                "ResultString": "Eve won 2-1-0",
            },
            {
                "Player": "Frank",
                "Opponent": "Grace",
                "Outcome": "Frank won",
                "ResultString": "Frank won 2-0-0",
            },
            {
                "Player": "Heidi",
                "Opponent": "Ivan",
                "Outcome": "Ivan won",
                "ResultString": "0-0-3 Draw",
            },
        ]
    )

    lookup = build_pilot_result_lookup_from_pairings(
        pairings,
        ["Alice", "Bob", "Frank"],
        constructed_pilots={"Alice", "Bob", "Frank"},
    )

    assert lookup["Alice"] == {"Wins": 1, "Losses": 1}
    assert lookup["Bob"] == {"Wins": 0, "Losses": 0}
    assert lookup["Frank"] == {"Wins": 1, "Losses": 0}
