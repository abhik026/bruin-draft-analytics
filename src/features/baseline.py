"""Draft-slot baseline and surplus value. Owner: Member B.

One smoothed curve of outcome vs. overall pick, SHARED by all positions. (A separate
curve per position would force every position's average surplus to ~0.)
"""
import numpy as np
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess


def fit_baseline(df: pd.DataFrame, outcome_col: str = "outcome",
                 pick_col: str = "pick", frac: float = 0.3) -> pd.Series:
    """Return a Series indexed by pick number (1..max) holding the expected outcome."""
    d = df[[pick_col, outcome_col]].dropna()
    # it=0: no robustness iterations, so the curve tracks the MEAN (default it=3 pulls toward the median)
    fit = lowess(d[outcome_col], d[pick_col], frac=frac, it=0, return_sorted=True)
    curve = pd.DataFrame(fit, columns=[pick_col, "baseline"]).drop_duplicates(pick_col)
    picks = np.arange(1, int(df[pick_col].max()) + 1)
    base = np.interp(picks, curve[pick_col], curve["baseline"])
    return pd.Series(base, index=picks, name="baseline")


def add_surplus(df: pd.DataFrame, baseline: pd.Series,
                outcome_col: str = "outcome", pick_col: str = "pick") -> pd.DataFrame:
    """Add `baseline` and `surplus` (= outcome - baseline) columns."""
    out = df.copy()
    out["baseline"] = out[pick_col].astype(int).map(baseline)
    out["surplus"] = out[outcome_col] - out["baseline"]
    return out
