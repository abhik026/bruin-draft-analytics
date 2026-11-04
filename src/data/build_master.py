"""Build the master table: one row per drafted player. Owner: Member A.

    python -m src.data.build_master

NFL side (draft + players + combine + outcome) is DONE and runs now.
TODO (Member A, days 4-6): merge college stats from data/raw/college/. See README.
"""
import pandas as pd

from src.features.outcome import get_outcome
from src.utils import (CLASS_MAX, CLASS_MIN, PROCESSED, RAW_NFL, clean_name,
                       pick_tier, to_pos_group)


def _height_to_inches(ht) -> float:
    try:
        feet, inches = str(ht).split("-")
        return int(feet) * 12 + int(inches)
    except (ValueError, TypeError):
        return float("nan")


def build_nfl_side() -> pd.DataFrame:
    draft = pd.read_parquet(RAW_NFL / "draft_picks.parquet")
    combine = pd.read_parquet(RAW_NFL / "combine.parquet")
    players = pd.read_parquet(RAW_NFL / "players.parquet")

    df = draft[draft["season"].between(CLASS_MIN, CLASS_MAX)].copy()
    df = df.rename(columns={"pfr_player_name": "player_name",
                            "pfr_player_id": "pfr_id", "position": "pos_draft"})

    # position: finer players-table label first, draft-table label as fallback
    pl = players[["gsis_id", "position"]].rename(columns={"position": "pos_players"})
    df = df.merge(pl.drop_duplicates("gsis_id"), on="gsis_id", how="left")
    df["pos_raw"] = df["pos_players"].fillna(df["pos_draft"])
    # combine: one row per player, joined on the PFR id (97%+ match in testing)
    cb = (combine.assign(_n=combine.notna().sum(axis=1))
                 .sort_values("_n", ascending=False)
                 .drop_duplicates("pfr_id"))
    cb = cb.assign(height_in=cb["ht"].map(_height_to_inches), weight=cb["wt"],
                   pos_combine=cb["pos"], has_combine=True)
    keep = ["pfr_id", "height_in", "weight", "forty", "vertical", "broad_jump",
            "bench", "cone", "shuttle", "pos_combine", "has_combine"]
    df = df.merge(cb[keep], on="pfr_id", how="left")
    df["has_combine"] = df["has_combine"].fillna(False).astype(bool)

    # position group: players table -> combine label -> draft label (first one that resolves)
    df["pos_group"] = df["pos_players"].map(to_pos_group)
    for col in ["pos_combine", "pos_draft"]:
        df["pos_group"] = df["pos_group"].fillna(df[col].map(to_pos_group))

    df["name_clean"] = df["player_name"].map(clean_name)
    df["pick_tier"] = pick_tier(df["pick"])
    df["outcome"] = get_outcome(df)
    return df


def build_master() -> pd.DataFrame:
    df = build_nfl_side()
    # TODO (Member A): merge college stats here, then set has_college_match.
    df["has_college_match"] = False
    return df


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    m = build_master()
    m.to_parquet(PROCESSED / "master.parquet", index=False)
    print(f"master: {len(m):,} rows, classes {m.season.min()}-{m.season.max()}")
    print(f"combine match: {m.has_combine.mean():.1%} | outcome missing: {m.outcome.isna().mean():.1%}")
    print(f"position group unresolved/excluded: {m.pos_group.isna().sum()} rows")
    print(m.pos_group.value_counts().to_string())
