"""Combine coverage, player matching, and athletic-test analysis."""
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

from src.utils import CLASS_MAX, CLASS_MIN, POSITION_GROUPS, POSITION_MAP, clean_name, to_pos_group

COMBINE_COLS = ["height_in", "weight", "forty", "vertical", "broad_jump", "bench", "cone", "shuttle"]


def _key(row, columns):
    values = tuple(row[col] for col in columns)
    return None if any(pd.isna(value) or value == "" for value in values) else values


def _match_records(left, right, stages, checks):
    """Accept unique matches only; blank keys and conflicting known IDs never match."""
    matched = pd.Series(pd.NA, index=left.index, dtype="Int64")
    method = pd.Series("unmatched", index=left.index)
    for label, left_keys, right_keys in stages:
        lookup = {}
        for j, row in right.iterrows():
            key = _key(row, right_keys)
            if key is not None:
                lookup.setdefault(key, []).append(j)
        for i in matched[matched.isna()].index:
            row = left.loc[i]
            candidates = lookup.get(_key(row, left_keys), [])
            valid = []
            for j in candidates:
                other = right.loc[j]
                conflict = any(
                    pd.notna(row[a]) and row[a] != "" and pd.notna(other[b])
                    and other[b] != "" and row[a] != other[b]
                    for a, b in checks
                )
                if not conflict:
                    valid.append(j)
            if len(valid) == 1:
                matched.loc[i], method.loc[i] = valid[0], label
    duplicates = matched.notna() & matched.duplicated(keep=False)
    matched.loc[duplicates] = pd.NA
    method.loc[duplicates] = "ambiguous"
    return matched, method


def _height_inches(value):
    if pd.isna(value):
        return np.nan
    try:
        feet, inches = str(value).split("-")
        feet, inches = int(feet), int(inches)
        return feet * 12 + inches if 0 <= inches < 12 else np.nan
    except (ValueError, TypeError):
        return np.nan


def build_id_bridge(draft, combine, players, position_overrides=None):
    """Return one row per draft pick in the shared class window, including unmatched picks.

    Join the result to draft picks on (season, pick). Measurements come only from
    the combine table. Record indices refer to the cached input tables.
    Optional shared position overrides fill unresolved labels only.
    """
    d = draft.loc[draft.season.between(CLASS_MIN, CLASS_MAX)].copy().reset_index(drop=True)
    if d.duplicated(["season", "pick"]).any():
        raise ValueError("Draft picks must be unique on (season, pick).")
    d = d.rename(columns={"pfr_player_id": "pfr_id", "pfr_player_name": "player_name", "position": "pos_draft"})
    d["name_clean"] = d.player_name.map(clean_name)
    d["school_clean"] = d.college.map(clean_name)
    c = combine.copy().reset_index(drop=True)
    c["name_clean"] = c.player_name.map(clean_name)
    c["school_clean"] = c.school.map(clean_name)
    p = players.copy().reset_index(drop=True)
    p["name_clean"] = p.display_name.map(clean_name)
    p["school_clean"] = p.college_name.map(clean_name)

    combine_stages = [
        ("pfr_id_year", ["pfr_id", "season"], ["pfr_id", "season"]),
        ("draft_pick_name", ["season", "pick", "name_clean"], ["draft_year", "draft_ovr", "name_clean"]),
        ("name_year_school", ["name_clean", "season", "school_clean"], ["name_clean", "season", "school_clean"]),
    ]
    combine_checks = [("pfr_id", "pfr_id"), ("season", "season"),
                      ("season", "draft_year"), ("pick", "draft_ovr")]
    ci, cm = _match_records(d, c, combine_stages, combine_checks)
    player_stages = [
        ("pfr_id", ["pfr_id"], ["pfr_id"]),
        ("gsis_id", ["gsis_id"], ["gsis_id"]),
        ("draft_pick_name", ["season", "pick", "name_clean"], ["draft_year", "draft_pick", "name_clean"]),
        ("name_year_school", ["name_clean", "season", "school_clean"], ["name_clean", "draft_year", "school_clean"]),
    ]
    player_checks = [("pfr_id", "pfr_id"), ("gsis_id", "gsis_id"),
                     ("season", "draft_year"), ("pick", "draft_pick")]
    pi, pm = _match_records(d, p, player_stages, player_checks)

    bridge = d[["season", "round", "pick", "team", "player_name", "name_clean",
                "college", "pfr_id", "gsis_id", "pos_draft"]].copy()
    bridge["combine_row"] = ci
    bridge["player_row"] = pi
    bridge["combine_match_method"] = cm
    bridge["player_match_method"] = pm
    bridge["has_combine"] = ci.notna()
    bridge["has_player_match"] = pi.notna()
    for source, target in {
        "pfr_id": "combine_pfr_id", "season": "combine_season", "draft_year": "combine_draft_year",
        "draft_ovr": "combine_draft_pick", "player_name": "combine_name", "school": "combine_school",
        "pos": "pos_combine", "ht": "height_raw", "wt": "weight", "forty": "forty",
        "vertical": "vertical", "broad_jump": "broad_jump", "bench": "bench", "cone": "cone", "shuttle": "shuttle",
    }.items():
        bridge[target] = ci.map(c[source])
    for source, target in {
        "pfr_id": "players_pfr_id", "gsis_id": "players_gsis_id",
        "display_name": "players_name", "position": "pos_players",
    }.items():
        bridge[target] = pi.map(p[source])
    bridge["height_in"] = bridge.height_raw.map(_height_inches)
    for col in COMBINE_COLS:
        bridge[col] = pd.to_numeric(bridge[col], errors="raise")
    bridge["pos_group"] = pd.Series(None, index=bridge.index, dtype="object")
    bridge["position_source"] = "unresolved"
    for col in ["pos_players", "pos_combine", "pos_draft"]:
        group = bridge[col].map(to_pos_group)
        use = bridge.pos_group.isna() & group.notna()
        bridge.loc[use, "pos_group"] = group[use]
        bridge.loc[use, "position_source"] = col
    excluded = {key for key, value in POSITION_MAP.items() if value is None}
    bridge["excluded_position"] = bridge.pos_draft.isin(excluded)
    if position_overrides is not None:
        overrides = position_overrides[["season", "pick", "pos_group"]].copy()
        overrides["pos_group"] = overrides.pos_group.astype("string").str.strip().str.upper()
        overrides = overrides[overrides.pos_group.notna() & overrides.pos_group.ne("")]
        if overrides.duplicated(["season", "pick"]).any():
            raise ValueError("Position overrides must be unique on (season, pick).")
        if not overrides.pos_group.isin(POSITION_GROUPS).all():
            raise ValueError("Position overrides contain an unknown position group.")
        overrides = overrides.rename(columns={"pos_group": "pos_override"})
        bridge = bridge.merge(overrides, on=["season", "pick"], how="left", validate="one_to_one")
        use = bridge.pos_group.isna() & bridge.pos_override.notna() & ~bridge.excluded_position
        bridge.loc[use, "pos_group"] = bridge.loc[use, "pos_override"]
        bridge.loc[use, "position_source"] = "position_override"
        bridge = bridge.drop(columns="pos_override")
    bridge["position_unresolved"] = bridge.pos_group.isna() & ~bridge.excluded_position
    bridge["pos_group"] = bridge.pos_group.astype("string")
    return bridge


def combine_coverage(df, by="pos_group"):
    """Fraction with each measurement; callers supply all drafted players in the cohort."""
    return df.groupby(by, observed=True, dropna=False)[COMBINE_COLS].agg(lambda s: s.notna().mean()).round(4)


def coverage_counts(df, by="pos_group"):
    """Long table of measured counts, drafted-player denominators, and coverage."""
    groups = [by] if isinstance(by, str) else list(by)
    grouped = df.groupby(groups, observed=True, dropna=False)
    counts = grouped[COMBINE_COLS].count().reset_index().melt(
        id_vars=groups, var_name="test", value_name="n_measured"
    )
    totals = grouped.size().rename("n_drafted").reset_index()
    counts = counts.merge(totals, on=groups, validate="many_to_one")
    counts["coverage"] = counts.n_measured / counts.n_drafted
    return counts


def size_speed_profiles(df, by="pos_group"):
    """Mean height (in), weight (lb), and 40 time (s), with each measurement's n."""
    return df.groupby(by, observed=True)[["height_in", "weight", "forty"]].agg(["count", "mean", "std"])


def test_surplus_correlations(df, outcome_col="surplus", min_n=20, n_boot=1000, seed=42):
    """Spearman rho and player-bootstrap 95% intervals for complete pairs, by position.

    These are descriptive intervals, not a correction for examining many tests.
    Missing tests and outcomes are not filled with zero.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for position, group in df.groupby("pos_group", observed=True):
        for test in COMBINE_COLS:
            pairs = group[[test, outcome_col]].dropna().to_numpy(dtype=float)
            n = len(pairs)
            rho = lo = hi = np.nan
            if n >= min_n and np.unique(pairs[:, 0]).size > 1 and np.unique(pairs[:, 1]).size > 1:
                rho = float(spearmanr(pairs[:, 0], pairs[:, 1]).statistic)
                sampled = pairs[rng.integers(0, n, size=(n_boot, n))]
                x = rankdata(sampled[:, :, 0], axis=1)
                y = rankdata(sampled[:, :, 1], axis=1)
                x -= x.mean(axis=1, keepdims=True)
                y -= y.mean(axis=1, keepdims=True)
                denominator = np.sqrt((x*x).sum(axis=1) * (y*y).sum(axis=1))
                boot = np.divide((x*y).sum(axis=1), denominator,
                                 out=np.full(n_boot, np.nan), where=denominator != 0)
                lo, hi = np.nanquantile(boot, [0.025, 0.975])
            rows.append({"pos_group": position, "test": test, "n": n,
                         "rho": rho, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)