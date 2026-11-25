import numpy as np, pandas as pd
from src.data.build_master import attach_college_ids, attach_college
from src.features.baseline import shrunk_position_effects
from src.features.outcome import get_rookie_window_outcome
from src.utils import to_pos_group


def test_negative_college_id_is_not_a_match():
    df = pd.DataFrame({"season": [2015], "pick": [10], "name_clean": ["john doe"]})
    picks = pd.DataFrame({"year": [2015], "overall": [10], "collegeAthleteId": [-5.0],
                          "name": ["John Doe"], "collegeTeam": ["X"]})
    out = attach_college_ids(df, picks)
    assert out["college_athlete_id"].isna().all()


def test_zero_placeholder_stats_do_not_count():
    df = pd.DataFrame({"season": [2015], "pick": [10], "name_clean": ["john doe"]})
    picks = pd.DataFrame({"year": [2015], "overall": [10], "collegeAthleteId": [7.0],
                          "name": ["John Doe"], "collegeTeam": ["X"]})
    stats = pd.DataFrame({"season": [2014], "playerId": ["7"], "category": ["defensive"],
                          "statType": ["TOT"], "stat": ["0"], "team": ["X"], "file_year": [2014]})
    import src.data.build_master as bm
    bm._read_year_files = lambda k: picks if k == "draft_picks" else stats
    out = attach_college(df)
    assert out["has_college_match"].iloc[0] and not out["has_college_stats"].iloc[0]


def test_shrinkage_pulls_small_groups():
    d = pd.DataFrame({"pos_group": ["A"] * 5 + ["B"] * 500, "surplus": [10.0] * 5 + [1.0] * 500})
    r = shrunk_position_effects(d, k=50)
    assert r.loc["A", "shrunk"] < 1.5 and r.loc["B", "shrunk"] > 0.8


def test_rookie_outcome_counts_four_seasons_only():
    df = pd.DataFrame({"pfr_id": ["P1"], "season": [2015]}, index=[0])
    rows = [dict(game_id=f"{y}_{w}", game_type="REG", season=y, team="T", pfr_player_id="P1",
                 offense_pct=1.0, defense_pct=0.0) for y in range(2015, 2021) for w in range(1, 3)]
    out = get_rookie_window_outcome(df, pd.DataFrame(rows))
    assert abs(out.iloc[0] - 4.0) < 1e-9


def test_fullback_not_grouped():
    assert to_pos_group("FB") is None
