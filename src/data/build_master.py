"""Build the master table: one row per drafted player. Owner: Member A.
 
    python -m src.data.build_master
 
Pipeline
  1. NFL side: draft picks + players + combine + outcome            (build_nfl_side)
  2. Position cleanup: drop K/P/LS, apply manual overrides for DB/OL (apply_position_cleanup)
  3. College side: CFBD draft-pick id lookup, then final-season stats (attach_college)
"""
import pandas as pd
 
from src.features.outcome import get_outcome
from src.utils import (CLASS_MAX, CLASS_MIN, INTERIM, PROCESSED, RAW_COLLEGE, RAW_NFL,
                       ROOT, clean_name, pick_tier, to_pos_group)
 
OVERRIDES_PATH = ROOT / "src" / "data" / "position_overrides.csv"
EXCLUDED_POS = {"K", "P", "LS"}            # plan: kickers, punters, long snappers are out
 
# nflverse draft_picks carries NFL career stats (pass_yards, def_sacks...). Those names
# collide with the college features the plan wants, so build_nfl_side prefixes them nfl_.
NFL_STAT_COLS = ["pass_completions", "pass_attempts", "pass_yards", "pass_tds", "pass_ints",
                 "rush_atts", "rush_yards", "rush_tds", "receptions", "rec_yards", "rec_tds",
                 "def_solo_tackles", "def_ints", "def_sacks"]
# CFBD stat types that are rates / one-offs; recompute from counts later instead of summing
SKIP_STAT_TYPES = {"YPA", "YPC", "YPR", "PCT", "LONG", "AVG", "PTS"}
CAT_PREFIX = {"passing": "pass", "rushing": "rush", "receiving": "rec", "defensive": "def",
              "interceptions": "dint", "fumbles": "fum", "kickReturns": "kr",
              "puntReturns": "pr", "kicking": "k", "punting": "p"}
 
 
# ----------------------------------------------------------------------------- NFL side
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
    # NFL career stats get an nfl_ prefix so they can never be confused with college features.
    # (w_av, dr_av, games, seasons_started etc. keep their names: get_outcome() uses them.)
    df = df.rename(columns={c: f"nfl_{c}" for c in NFL_STAT_COLS if c in df.columns})
 
    pl = players[["gsis_id", "position"]].rename(columns={"position": "pos_players"})
    df = df.merge(pl.drop_duplicates("gsis_id"), on="gsis_id", how="left")
    df["pos_raw"] = df["pos_players"].fillna(df["pos_draft"])
 
    cb = (combine.assign(_n=combine.notna().sum(axis=1))
                 .sort_values("_n", ascending=False)
                 .drop_duplicates("pfr_id"))
    cb = cb.assign(height_in=cb["ht"].map(_height_to_inches), weight=cb["wt"],
                   pos_combine=cb["pos"], has_combine=True)
    keep = ["pfr_id", "height_in", "weight", "forty", "vertical", "broad_jump",
            "bench", "cone", "shuttle", "pos_combine", "has_combine"]
    df = df.merge(cb[keep], on="pfr_id", how="left")
    df["has_combine"] = df["has_combine"].fillna(False).astype(bool)
 
    df["pos_group"] = df["pos_players"].map(to_pos_group)
    for col in ["pos_combine", "pos_draft"]:
        df["pos_group"] = df["pos_group"].fillna(df[col].map(to_pos_group))
 
    df["name_clean"] = df["player_name"].map(clean_name)
    df["pick_tier"] = pick_tier(df["pick"])
    df["outcome"] = get_outcome(df)
    return df
 
 
# ----------------------------------------------------------------------------- positions
def apply_position_cleanup(df: pd.DataFrame) -> pd.DataFrame:
    """Drop K/P/LS, then fill unresolved DB/OL labels from the hand-curated overrides file."""
    is_excl = (df["pos_raw"].str.upper().isin(EXCLUDED_POS)
               | df["pos_draft"].str.upper().isin(EXCLUDED_POS))
    df = df[~is_excl].copy()
 
    if OVERRIDES_PATH.exists():
        ov = pd.read_csv(OVERRIDES_PATH, usecols=["season", "pick", "pos_group"],
                         dtype={"pos_group": "string"})
        ov["pos_group"] = ov["pos_group"].str.strip().str.upper()   # tolerate " cb", "Cb"
        ov = ov[ov["pos_group"].notna() & (ov["pos_group"] != "")]
        bad = set(ov["pos_group"]) - set(["QB", "RB", "WR", "TE", "OT", "IOL", "EDGE",
                                          "IDL", "LB", "CB", "S"])
        if bad:
            raise ValueError(f"position_overrides.csv has invalid pos_group values: {bad}")
        ov = ov.rename(columns={"pos_group": "pos_override"})
        print(f"[info] position overrides applied: {len(ov)} rows from {OVERRIDES_PATH.name}")
        df = df.merge(ov, on=["season", "pick"], how="left")
        df["pos_group"] = df["pos_group"].fillna(df["pos_override"])
        df = df.drop(columns="pos_override")
    return df
 
 
# ----------------------------------------------------------------------------- college side
def _read_year_files(kind: str) -> pd.DataFrame:
    files = sorted(RAW_COLLEGE.glob(f"{kind}_*.parquet"))
    if not files:
        return pd.DataFrame()
    parts = []
    for f in files:
        d = pd.read_parquet(f)
        if len(d):
            d["file_year"] = int(f.stem.split("_")[-1])
            parts.append(d)
    return pd.concat(parts, ignore_index=True)
 
 
def _id_str(series: pd.Series) -> pd.Series:
    """Ids as clean strings: 13223, 13223.0 and '13223' all become '13223'."""
    return pd.to_numeric(series, errors="coerce").astype("Int64").astype("string")
 
 
def _last_token(name) -> str:
    toks = clean_name(name).split()
    return toks[-1] if toks else ""
 
 
def attach_college_ids(df: pd.DataFrame, picks: pd.DataFrame) -> pd.DataFrame:
    """Link each NFL pick to a CFBD college athlete id.
 
    Method 1 (preferred): exact (season, overall pick). Accepted only if last names agree.
    Method 2 (fallback):  (season, cleaned full name).
    The method used is stored in `college_match_method` so match quality is auditable.
    """
    need = {"year", "overall", "collegeAthleteId", "name"}
    if not need <= set(picks.columns):
        raise KeyError(f"CFBD draft_picks is missing {need - set(picks.columns)}. "
                       f"Columns found: {list(picks.columns)}. Fix the rename below.")
    # CFBD also has its own `pick` column (pick within the round): drop it, we want `overall`
    cols = [c for c in ["year", "overall", "collegeAthleteId", "name", "collegeTeam"]
            if c in picks.columns]
    p = picks[cols].rename(columns={"year": "season", "overall": "pick",
                                    "collegeAthleteId": "college_athlete_id",
                                    "name": "cfbd_name", "collegeTeam": "cfbd_school"})
    if "cfbd_school" not in p:
        p["cfbd_school"] = pd.NA
    p["college_athlete_id"] = _id_str(p["college_athlete_id"])
    p["name_clean_cfbd"] = p["cfbd_name"].map(clean_name)
    p = p[["season", "pick", "college_athlete_id", "cfbd_name", "cfbd_school",
           "name_clean_cfbd"]].dropna(subset=["college_athlete_id"])
 
    # method 1: pick key + last-name sanity check
    m1 = df[["season", "pick", "name_clean"]].merge(
        p.drop_duplicates(["season", "pick"]), on=["season", "pick"], how="left")
    ok = m1["college_athlete_id"].notna() & (m1["name_clean"].map(_last_token)
                                              == m1["cfbd_name"].map(_last_token))
    m1.loc[~ok, ["college_athlete_id", "cfbd_name", "cfbd_school"]] = pd.NA
    m1["college_match_method"] = ok.map({True: "pick", False: None})
 
    # method 2: full-name fallback for rows method 1 missed
    p2 = p.drop_duplicates(["season", "name_clean_cfbd"], keep=False)
    fb = m1.loc[~ok, ["season", "pick", "name_clean"]].merge(
        p2, left_on=["season", "name_clean"], right_on=["season", "name_clean_cfbd"],
        how="inner", suffixes=("", "_p"))
    fb = fb.drop_duplicates(["season", "pick"]).set_index(["season", "pick"])
 
    out = df.merge(m1.drop(columns="name_clean"), on=["season", "pick"], how="left")
    idx = pd.MultiIndex.from_frame(out[["season", "pick"]])
    need_fb = out["college_athlete_id"].isna() & idx.isin(fb.index)
    for col in ["college_athlete_id", "cfbd_name", "cfbd_school"]:
        out.loc[need_fb, col] = fb[col].reindex(idx[need_fb]).to_numpy()
    out.loc[need_fb, "college_match_method"] = "name"
    out["college_match_method"] = out["college_match_method"].fillna("none")
    return out
 
 
def build_college_features(stats: pd.DataFrame, ids: pd.DataFrame) -> pd.DataFrame:
    """Wide table: one row per college athlete, stats from their FINAL season before the draft.
 
    ids: columns college_athlete_id, season (draft year).
    """
    need = {"playerId", "category", "statType", "stat"}
    if not need <= set(stats.columns):
        raise KeyError(f"CFBD player_stats is missing {need - set(stats.columns)}. "
                       f"Columns found: {list(stats.columns)}")
    s = stats.copy()
    s["college_athlete_id"] = _id_str(s["playerId"])
    s["stat_season"] = s["season"] if "season" in s.columns else s["file_year"]
    ids = ids.rename(columns={"season": "draft_season"}).drop_duplicates("college_athlete_id")
    s = s.drop(columns=["season"], errors="ignore")             # avoid clashing with the draft year
    s = s.merge(ids, on="college_athlete_id", how="inner")
    s = s[s["stat_season"] < s["draft_season"]]                 # strictly before the draft
    last = s.groupby("college_athlete_id")["stat_season"].transform("max")
    s = s[s["stat_season"] == last]
    s = s[~s["statType"].isin(SKIP_STAT_TYPES)]
    s["stat"] = pd.to_numeric(s["stat"], errors="coerce")
    s["col"] = (s["category"].map(CAT_PREFIX).fillna(s["category"].str.lower()) + "_"
                + s["statType"].str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True))
    wide = (s.pivot_table(index="college_athlete_id", columns="col", values="stat",
                          aggfunc="sum")                    # sum handles mid-year transfers
              .reset_index())
    wide = wide.merge(s.groupby("college_athlete_id", as_index=False)
                        .agg(college_final_season=("stat_season", "max"),
                             college_team_final=("team", "first")),
                      on="college_athlete_id")
    return wide
 
 
def attach_college(df: pd.DataFrame) -> pd.DataFrame:
    picks = _read_year_files("draft_picks")
    stats = _read_year_files("player_stats")
    if picks.empty:
        print("[warn] no college data in data/raw/college/: has_college_match = False for all")
        df["has_college_match"] = False
        df["has_college_stats"] = False
        df["college_match_method"] = "none"
        return df
    df = attach_college_ids(df, picks)
    df["has_college_match"] = df["college_athlete_id"].notna()
    df["has_college_stats"] = False
    if not stats.empty:
        feats = build_college_features(stats, df[["college_athlete_id", "season"]].dropna())
        stat_cols = [c for c in feats.columns
                     if c not in {"college_athlete_id", "college_final_season", "college_team_final"}]
        df = df.merge(feats, on="college_athlete_id", how="left")
        df["has_college_stats"] = df[stat_cols].notna().any(axis=1)
    return df
 
 
# ----------------------------------------------------------------------------- reporting
def match_report(m: pd.DataFrame):
    """Match rates by position group and draft year (the Task 6 deliverable)."""
    by_pos = (m.groupby("pos_group", observed=True)
                .agg(n=("pick", "size"),
                     id_match=("has_college_match", "mean"),
                     stats_match=("has_college_stats", "mean"))
                .round(3).sort_values("id_match"))
    by_year = (m.groupby("season")
                 .agg(n=("pick", "size"),
                      id_match=("has_college_match", "mean"),
                      stats_match=("has_college_stats", "mean")).round(3))
    methods = m["college_match_method"].value_counts()
    return by_pos, by_year, methods
 
 
def unmatched_players(m: pd.DataFrame) -> pd.DataFrame:
    cols = ["season", "round", "pick", "player_name", "pos_group", "college", "pfr_id"]
    return m.loc[~m["has_college_match"], cols].sort_values(["season", "pick"])
 
 
def build_master() -> pd.DataFrame:
    df = build_nfl_side()
    df = apply_position_cleanup(df)
    return attach_college(df)
 
 
if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    m = build_master()
    m.to_parquet(PROCESSED / "master.parquet", index=False)
    print(f"master: {len(m):,} rows, classes {m.season.min()}-{m.season.max()}")
    print(f"combine match: {m.has_combine.mean():.1%} | outcome missing: {m.outcome.isna().mean():.1%}")
    print(f"position group unresolved: {m.pos_group.isna().sum()} rows (fill src/data/position_overrides.csv)")
    print(f"college id match: {m.has_college_match.mean():.1%}")
    print(m.pos_group.value_counts().to_string())