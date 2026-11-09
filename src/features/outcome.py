"""The ONE definition of 'NFL success' everyone uses. Owner: Member C (Vincent).

FINAL DEFINITION (Nov 2026)
  outcome = w_av (PFR weighted career Approximate Value) from nflverse draft_picks,
            with missing values set to 0.
  Main analysis window: draft classes 2010-2018 (MATURE_CLASS_MAX).

WHY
  - `car_av` is EMPTY for every class, and there is no per-season AV, so a true
    4-year AV cannot be built from nflverse.
  - Missing w_av = never played: 239 picks (2010-2022) have no w_av and none
    have any NFL games. They count as 0 (busts), not missing.
  - Career length: mean w_av is flat (~16-19) for 2010-2018, then falls for
    2019-2022 because those careers aren't finished. Dividing by seasons possible
    overcorrects (reverses the trend), so we restrict to mature classes instead.
  - w_av tracks playing time well: Spearman 0.92 with games, 0.89 with seasons
    started (weakest: RB, 0.71, because AV gives fullbacks ~0 credit).

ROBUSTNESS CHECK
  get_contract_outcome(): best non-rookie contract, APY as % of salary cap.
  Spearman 0.85 with w_av. Contracts favor QB/TE/CB more than AV does, and
  IOL/RB less. Report position results under BOTH metrics.

KNOWN LIMITATIONS
  - AV credits QBs most per starting season; undervalues blocking TEs and safeties.
  - AV scores fullbacks near 0 (recommend excluding FB or a separate group).
  - Contracts reflect the positional market, not just on-field production.
"""
import pandas as pd

from src.utils import LAST_COMPLETE_SEASON

OUTCOME_METRIC = "w_av"
MATURE_CLASS_MAX = 2018   # last class with >= 7 completed seasons; see notebook 03


def get_outcome(df: pd.DataFrame, metric: str | None = None) -> pd.Series:
    """Return the outcome series for a draft-picks-style dataframe.

    Missing values mean the player never appeared in an NFL game, so they are 0.
    """
    return df[metric or OUTCOME_METRIC].astype(float).fillna(0)


def mature_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only draft classes whose careers have had time to mature (<= 2018)."""
    return df[df["season"] <= MATURE_CLASS_MAX]


def get_contract_outcome(df: pd.DataFrame, contracts: pd.DataFrame) -> pd.Series:
    """Robustness-check outcome: each player's best NON-rookie contract (APY % of cap).

    df: needs a `gsis_id` column (e.g. the master table).
    contracts: the nflverse contracts table (data/raw/nfl/contracts.parquet).
    Players with no second contract get 0 (no team paid him after his rookie deal).
    """
    second = contracts[contracts["year_signed"] > contracts["draft_year"]]
    best = (second.dropna(subset=["gsis_id"])
                  .groupby("gsis_id")["apy_cap_pct"].max())
    return df["gsis_id"].map(best).fillna(0).astype(float).rename("contract_value")


def add_career_length(df: pd.DataFrame) -> pd.DataFrame:
    """Add `seasons_possible`: completed NFL seasons since the draft."""
    out = df.copy()
    out["seasons_possible"] = (LAST_COMPLETE_SEASON - out["season"] + 1).clip(lower=0)
    return out