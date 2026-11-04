"""The ONE definition of 'NFL success' everyone uses. Owner: Member C.

FINDINGS (verified against nflverse draft_picks, Nov 2026):
  - `car_av` (career AV) is EMPTY for every class. Do not use it.
  - There is NO per-season AV, so a true '4-year AV' cannot be built from this table.
  - Available: `w_av` (PFR weighted career AV), `dr_av` (AV with the drafting team only),
    `seasons_started`, `games`, `to` (last season played).

PROVISIONAL CHOICE: `w_av`. Known problem: older classes have had longer to accumulate
value, so w_av is not comparable across classes without adjustment. Member C decides
how to handle it (restrict the window, divide by seasons in league, or use dr_av as a
robustness check) and updates this file. Everyone else just calls get_outcome().
"""
import pandas as pd

from src.utils import LAST_COMPLETE_SEASON

OUTCOME_METRIC = "w_av"


def get_outcome(df: pd.DataFrame, metric: str | None = None) -> pd.Series:
    """Return the outcome series for a draft-picks-style dataframe."""
    return df[metric or OUTCOME_METRIC].astype(float)


def add_career_length(df: pd.DataFrame) -> pd.DataFrame:
    """Add `seasons_possible`: completed NFL seasons since the draft (for adjusting w_av)."""
    out = df.copy()
    out["seasons_possible"] = (LAST_COMPLETE_SEASON - out["season"] + 1).clip(lower=0)
    return out
