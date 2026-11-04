"""Pull NFL tables from nflverse and cache them as parquet. Owner: Member A.

No API key needed. Run from the repo root:
    python -m src.data.pull_nfl            # skip tables already cached
    python -m src.data.pull_nfl --force    # re-pull everything
"""
import argparse

import nflreadpy as nfl

from src.utils import RAW_NFL

TABLES = {
    "draft_picks": nfl.load_draft_picks,
    "combine": nfl.load_combine,
    "players": nfl.load_players,
    "contracts": nfl.load_contracts,   # used by Member C to test a contract-based outcome
}


def pull_nfl(force: bool = False) -> None:
    RAW_NFL.mkdir(parents=True, exist_ok=True)
    for name, loader in TABLES.items():
        path = RAW_NFL / f"{name}.parquet"
        if path.exists() and not force:
            print(f"[skip] {name} already cached")
            continue
        df = loader().to_pandas()
        df.to_parquet(path, index=False)
        print(f"[ok]   {name}: {len(df):,} rows -> {path.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    pull_nfl(ap.parse_args().force)
