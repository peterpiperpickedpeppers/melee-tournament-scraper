#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers

import pandas as pd

# This module provides archetype_card_copy_winrates(df, archetype, ...)

def archetype_card_copy_winrates(
    df: pd.DataFrame,
    archetype: str,
    loc: str | None = None,   # None (or "None") => include both main + side
    min_pilots: int = 0,
    max_copies_cap: int | None = None,
) -> pd.DataFrame:
    """
    For the given archetype, return a table that, for each card (and loc),
    shows winrate by copy count INCLUDING 0 copies (pilots who didn't play it).
    Expected columns in df (case-insensitive): player|pilot, archetype, card name|card,
    quantity|Copies, loc, wins|Wins, losses|Losses
    """

    # --- normalize columns ---
    ren = {
        "player": "pilot",
        "card_name": "card",
        "qty": "Copies",
        "zone": "loc",
        "wins": "Wins",
        "losses": "Losses",
    }
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    # make sure required columns exist
    required = {"pilot", "deck_archetype", "card", "Copies", "loc", "Wins", "Losses"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    # coerce types gently
    df["Copies"] = pd.to_numeric(df["Copies"], errors="coerce").fillna(0).astype(int)
    df["Wins"]   = pd.to_numeric(df["Wins"],   errors="coerce").fillna(0).astype(int)
    df["Losses"] = pd.to_numeric(df["Losses"], errors="coerce").fillna(0).astype(int)

    # --- subset to archetype ---
    df_arch_all = df[df["deck_archetype"] == archetype].copy()
    if df_arch_all.empty:
        return pd.DataFrame(columns=["card","loc","deck_archetype","Copies","# of Pilots","Wins","Losses","Win%"])

    # normalize loc argument
    if isinstance(loc, str) and loc.lower() == "none":
        loc = None

    # optional loc filter for card rows ONLY (results still come from all pilots)
    if loc is not None and loc.lower() in ("main", "side"):
        df_arch = df_arch_all[df_arch_all["loc"].str.lower() == loc.lower()].copy()
    else:
        df_arch = df_arch_all.copy()  # include both

    # --- pilot-level results (use all archetype rows so every pilot is present) ---
    pilot_results = (
        df_arch_all.groupby("pilot")[["Wins", "Losses"]]
        .first()
        .reindex(df_arch_all["pilot"].unique())
    )
    all_pilots = pilot_results.index

    rows = []

    # iterate over (card, loc) pairs present in the (optionally) loc-filtered frame
    for (card, card_loc) in df_arch[["card", "loc"]].drop_duplicates().itertuples(index=False):
        # copies per pilot for THIS (card, loc); pilots without the card get 0
        sub = df_arch[(df_arch["card"] == card) & (df_arch["loc"] == card_loc)]
        copies_per_pilot = (
            sub.groupby("pilot")["Copies"].sum()
            .reindex(all_pilots, fill_value=0)
        )

        # decide copy range
        observed_max = int(copies_per_pilot.max()) if len(copies_per_pilot) else 0
        max_c = max_copies_cap if max_copies_cap is not None else observed_max
        copy_vals = range(0, max_c + 1)

        for c in copy_vals:
            pilots_at_c = copies_per_pilot.index[copies_per_pilot == c]
            n_pilots = len(pilots_at_c)
            if n_pilots < min_pilots:
                continue

            if n_pilots > 0:
                wr = pilot_results.loc[pilots_at_c].sum()
                wins = int(wr["Wins"])
                losses = int(wr["Losses"])
                total = wins + losses
                winp = round(100 * wins / total, 2) if total else 0.0
            else:
                wins = losses = 0
                winp = 0.0

            rows.append({
                "card": card,
                "loc": card_loc,
                "deck_archetype": archetype,
                "Copies": int(c),
                "# of Pilots": int(n_pilots),
                "Wins": int(wins),
                "Losses": int(losses),
                "Win%": winp,
            })

    out = pd.DataFrame(rows).sort_values(["card", "loc", "Copies"]).reset_index(drop=True)
    return out

