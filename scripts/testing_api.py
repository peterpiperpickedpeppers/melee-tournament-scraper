#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers


from bs4 import BeautifulSoup
import json
import pandas as pd
import ast
import numpy as np
from dotenv import load_dotenv
from utils.api_utils import _make_payload, _maybe_get_csrf_header, fetch_round_standings, extract_display_names

load_dotenv()

if __name__ == "__main__":
    event = "RC Houston"
    EVENT_ID = 248718
    ROUND_ID = 865063
    PAGE_SIZE = 400

    df = fetch_round_standings(ROUND_ID, EVENT_ID, page_size=PAGE_SIZE)
    print(f"\nTotal rows fetched: {len(df)}")

    # Add PlayerName column from the Team column
    df["PlayerName"] = df["Team"].apply(extract_display_names)

    # Move PlayerName to the front
    cols = ["PlayerName"] + [c for c in df.columns if c != "PlayerName"]
    df = df[cols]

    out_csv = fr"C:\Users\jjwey\OneDrive\Desktop\{event} round_{ROUND_ID}_standings222.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_csv}")