"""Pull college data from the CollegeFootballData API (the source behind cfbfastR).
Owner: Member D.   ONLY ONE PERSON needs to run this; share the cached files (see README).

Setup: free key from collegefootballdata.com -> put CFBD_API_KEY in your .env file.

    python -m src.data.pull_college --check          # 1 call/year: row counts per season
    python -m src.data.pull_college                  # pull stats + draft picks, cache as parquet
    python -m src.data.pull_college --start 2008 --end 2022

NOTE: this script calls the REST API directly with `requests` (fewer moving parts than
the cfbd package). It was written without live API access, so the first real run may need
small fixes: endpoint params and response fields are listed in the CFBD docs
(api.collegefootballdata.com). The free tier has a monthly call limit: results are cached,
so never re-pull inside a notebook.
"""
import argparse
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import CLASS_MAX, CLASS_MIN, RAW_COLLEGE

BASE = "https://api.collegefootballdata.com"


def _get(endpoint: str, params: dict, retries: int = 3):
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        raise SystemExit("CFBD_API_KEY not set. Copy .env.example to .env and add your key.")
    for attempt in range(retries):
        r = requests.get(f"{BASE}{endpoint}", params=params,
                         headers={"Authorization": f"Bearer {key}"}, timeout=60)
        if r.status_code == 429:           # rate limited: back off and retry
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Rate limited too many times on {endpoint} {params}")


def pull_year(kind: str, year: int, force: bool = False) -> pd.DataFrame | None:
    """kind: 'player_stats' (long format: player, team, category, statType, stat)
             'draft_picks'  (college athlete id <-> overall pick: the college<->NFL join key)"""
    RAW_COLLEGE.mkdir(parents=True, exist_ok=True)
    path = RAW_COLLEGE / f"{kind}_{year}.parquet"
    if path.exists() and not force:
        print(f"[skip] {path.name}")
        return pd.read_parquet(path)
    if kind == "player_stats":
        data = _get("/stats/player/season", {"year": year})
    elif kind == "draft_picks":
        data = _get("/draft/picks", {"year": year})
    else:
        raise ValueError(kind)
    df = pd.DataFrame(data)
    df.to_parquet(path, index=False)
    print(f"[ok]   {path.name}: {len(df):,} rows")
    return df


if __name__ == "__main__":
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=CLASS_MIN - 1)  # college season before draft
    ap.add_argument("--end", type=int, default=CLASS_MAX)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true", help="print row counts per season only")
    a = ap.parse_args()
    for yr in range(a.start, a.end + 1):
        pull_year("player_stats", yr, a.force)
        if not a.check:
            pull_year("draft_picks", yr, a.force)
