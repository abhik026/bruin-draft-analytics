"""Combine / athletic-testing helpers. Owner: Member E."""
import pandas as pd

COMBINE_COLS = ["height_in", "weight", "forty", "vertical", "broad_jump", "bench", "cone", "shuttle"]


def combine_coverage(df: pd.DataFrame, by: str = "pos_group") -> pd.DataFrame:
    """Share of players with each test, by position group (or any column in `by`)."""
    return df.groupby(by, observed=True)[COMBINE_COLS].agg(lambda s: s.notna().mean()).round(2)
