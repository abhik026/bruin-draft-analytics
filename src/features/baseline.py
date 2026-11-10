"""Draft-slot baseline and surplus value. Owner: Member B.

Definitions used by the whole project:

- **Baseline (expected outcome at a pick):** ONE smoothed curve of outcome vs. overall
  pick, fit on ALL players regardless of position. It answers "what does this draft
  slot typically return?" A separate curve per position would force every position's
  average surplus to ~0 by construction, so positions could not be ranked.
- **Smoother:** LOWESS (local weighted straight-line fits) with no robustness
  iterations (`it=0`), so the curve tracks the MEAN outcome at each pick, stars
  included. `frac=0.1` (a window of ~25 picks) was chosen in
  notebooks/02_draft_value_b.ipynb, section 4.
- **Tail cap:** picks after the last pick that every draft class reaches are pooled
  at that pick (only 1-10 players per pick otherwise), so they cannot bend the curve.
- **Surplus:** actual outcome minus the baseline at that player's (capped) pick.

Typical use (reproduces the notebook's heatmap inputs)::

    from src.features.baseline import fit_baseline, add_surplus
    baseline = fit_baseline(df)            # df: one row per drafted player
    df = add_surplus(df, baseline)         # adds `expected` and `surplus`
    table = surplus_table(df)              # position x pick tier: n, mean, 95% CI
"""
import numpy as np
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess

DEFAULT_FRAC = 0.1


def last_full_pick(df: pd.DataFrame, pick_col: str = "pick",
                   class_col: str = "season") -> int:
    """Return the last pick number that every draft class in `df` reaches.

    Picks 1..N appear once per class; draft length varies (compensatory picks), so
    beyond N some classes have no player. Example: classes 2010-2022 -> 253.
    """
    n_classes = df[class_col].nunique()
    n_per_pick = df.groupby(pick_col).size()
    short = n_per_pick[n_per_pick < n_classes].index
    return int(short.min() - 1) if len(short) else int(n_per_pick.index.max())


def fit_baseline(df: pd.DataFrame, outcome_col: str = "outcome",
                 pick_col: str = "pick", frac: float = DEFAULT_FRAC,
                 max_pick: int | None = None) -> pd.Series:
    """Fit the shared pick-value curve: expected outcome at each overall pick.

    Parameters
    ----------
    df : DataFrame with one row per drafted player (all positions together).
    outcome_col : column holding the outcome (e.g. from get_outcome()). Must have no
        NaN: a player who never played should be 0, not missing, or late picks are
        inflated. Fill before calling.
    pick_col : column holding the overall pick number (1 = first pick).
    frac : LOWESS window as a share of all players (0.1 ~ 25 picks wide).
    max_pick : picks above this are pooled at it before fitting. Default None uses
        last_full_pick(df), the last pick every class reaches.

    Returns
    -------
    pd.Series named "expected", indexed by pick 1..max_pick, holding the smoothed
    mean outcome at that pick. Look up any player with baseline.loc[pick]
    (or use add_surplus, which also handles picks past max_pick).
    """
    if df[outcome_col].isna().any():
        raise ValueError(
            f"{df[outcome_col].isna().sum()} rows have NaN '{outcome_col}'. Players who "
            "never played should count as 0; fill them (or drop them on purpose) first.")
    if max_pick is None:
        max_pick = last_full_pick(df, pick_col)

    x = df[pick_col].clip(upper=max_pick).to_numpy(dtype=float)
    y = df[outcome_col].to_numpy(dtype=float)

    # it=0: no robustness iterations, so the curve tracks the MEAN
    # (the default it=3 down-weights stars and pulls the curve toward the median)
    fit = lowess(y, x, frac=frac, it=0, return_sorted=True)

    # lowess returns one row per player; keep one value per distinct pick, then
    # fill every integer pick 1..max_pick (linear interpolation between picks)
    curve = pd.DataFrame(fit, columns=["pick", "value"]).drop_duplicates("pick")
    picks = np.arange(1, max_pick + 1)
    values = np.interp(picks, curve["pick"], curve["value"])
    return pd.Series(values, index=pd.Index(picks, name="pick"), name="expected")


def add_surplus(df: pd.DataFrame, baseline: pd.Series,
                outcome_col: str = "outcome", pick_col: str = "pick") -> pd.DataFrame:
    """Return a copy of `df` with `expected` and `surplus` columns added.

    expected = baseline value at the player's pick (picks beyond the last pick in
               `baseline` use that last value, matching the cap used in fitting)
    surplus  = outcome - expected   (in outcome units, e.g. AV; > 0 = beat the slot)

    `baseline` is the Series returned by fit_baseline.
    """
    out = df.copy()
    pick = out[pick_col].clip(upper=baseline.index.max())
    out["expected"] = baseline.reindex(pick).to_numpy()
    out["surplus"] = out[outcome_col] - out["expected"]
    return out


def cross_val_expected(df: pd.DataFrame, group_col: str = "season",
                       outcome_col: str = "outcome", pick_col: str = "pick",
                       frac: float = DEFAULT_FRAC, max_pick: int | None = None) -> pd.Series:
    """Out-of-fold baseline predictions: leave one group (draft class) out at a time.

    For each value of `group_col`, fits the baseline on all OTHER groups and predicts
    the held-out group's players, so no player's expected value uses his own outcome.
    This is the honest "pick slot only" benchmark for Layer 2: a player-level model
    must beat these predictions under the same split.

    `max_pick` defaults to last_full_pick(df) on the FULL data, so every fold uses
    the same cap. Returns a Series named "expected_cv", aligned to df.index.
    """
    if max_pick is None:
        max_pick = last_full_pick(df, pick_col, group_col)
    out = pd.Series(np.nan, index=df.index, name="expected_cv")
    for g in df[group_col].unique():
        held_out = df[group_col] == g
        curve = fit_baseline(df[~held_out], outcome_col, pick_col, frac, max_pick)
        out[held_out] = add_surplus(df[held_out], curve, outcome_col, pick_col)["expected"]
    return out


def bootstrap_ci(values, n_boot: int = 2000, ci: float = 0.95,
                 seed: int | None = 0) -> tuple[float, float]:
    """Percentile bootstrap confidence interval for the MEAN of `values`.

    Resamples `values` with replacement `n_boot` times, takes the mean of each
    resample, and returns the (lower, upper) percentiles covering `ci` of them
    (2.5th and 97.5th for ci=0.95). NaNs are ignored. Returns (nan, nan) for fewer
    than 2 values. Small samples give wide (and somewhat too narrow) intervals,
    so report n alongside the CI.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = rng.choice(v, size=(n_boot, len(v)), replace=True).mean(axis=1)
    tail = (1 - ci) / 2 * 100
    lo, hi = np.percentile(means, [tail, 100 - tail])
    return (float(lo), float(hi))


def surplus_table(df: pd.DataFrame, row: str = "pos_group", col: str = "pick_tier",
                  value: str = "surplus", min_n: int = 10, n_boot: int = 2000,
                  seed: int | None = 0) -> pd.DataFrame:
    """Summarize `value` (default surplus) for every row x col cell, one line per cell.

    Rows with a missing `row` or `col` label are dropped (e.g. unresolved positions).

    Returns a DataFrame indexed by (row, col) with columns:
      n            number of players in the cell
      mean         mean of `value`
      ci_low/high  bootstrap 95% CI for the mean (see bootstrap_ci)
      small        True if n < min_n: too few players to interpret; grey it out
      clear        True if the CI excludes 0 and the cell is not small: the cell
                   is confidently above (mean > 0) or below (mean < 0) its slot
    Pivot for a grid, e.g. table["mean"].unstack().
    """
    d = df.dropna(subset=[row, col, value])
    rows = []
    for (r, c), grp in d.groupby([row, col], observed=True):
        lo, hi = bootstrap_ci(grp[value], n_boot=n_boot, seed=seed)
        rows.append({row: r, col: c, "n": len(grp), "mean": grp[value].mean(),
                     "ci_low": lo, "ci_high": hi})
    out = pd.DataFrame(rows).set_index([row, col])
    out["small"] = out["n"] < min_n
    out["clear"] = ~out["small"] & ((out["ci_low"] > 0) | (out["ci_high"] < 0))
    return out
