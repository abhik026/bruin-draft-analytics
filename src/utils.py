"""Shared constants and helpers. Owner: Member A.

Everything the whole team must agree on lives here. If you need to change a
definition (position map, class window, pick tiers), change it HERE in a PR
and tell the team. Never redefine these in a notebook.
"""
from pathlib import Path
import re
import unicodedata

import pandas as pd

# ---------- paths ----------
ROOT = Path(__file__).resolve().parents[1]
RAW_NFL = ROOT / "data" / "raw" / "nfl"
RAW_COLLEGE = ROOT / "data" / "raw" / "college"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"

# ---------- scope (PROVISIONAL: confirm after the college coverage check) ----------
CLASS_MIN, CLASS_MAX = 2010, 2022   # draft classes in the analysis window
LAST_COMPLETE_SEASON = 2025         # most recent finished NFL season

# ---------- pick tiers (single picks are too noisy to compare positions) ----------
PICK_BINS = [0, 5, 15, 32, 64, 100, 400]
PICK_LABELS = ["1-5", "6-15", "16-32", "33-64", "65-100", "101+"]


def pick_tier(pick: pd.Series) -> pd.Series:
    """Map overall pick numbers to tier labels."""
    return pd.cut(pick, bins=PICK_BINS, labels=PICK_LABELS)


# ---------- position groups ----------
# nflverse position labels are messy: the draft table says DB / DE / OL, while the
# players table is finer (CB, FS, SS, OLB, OT, G, C). build_master.py tries the
# players-table label first, then falls back to the draft-table label.
# None = excluded from the analysis.
# OPEN DECISION: the EDGE vs LB boundary (DE and OLB both map to EDGE below).
# Members B and E should look at weights and sack production to sanity-check it.
POSITION_MAP = {
    "QB": "QB",
    "RB": "RB", "HB": "RB", "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "T": "OT", "OT": "OT",
    "G": "IOL", "OG": "IOL", "C": "IOL",
    "DE": "EDGE", "OLB": "EDGE", "EDGE": "EDGE",
    "DT": "IDL", "NT": "IDL", "DL": "IDL",
    "LB": "LB", "ILB": "LB", "MLB": "LB",
    "CB": "CB",
    "S": "S", "FS": "S", "SS": "S", "SAF": "S",
    "K": None, "P": None, "LS": None, "KR": None, "PR": None,
    # ambiguous labels (OL, DB) are deliberately NOT mapped: they get NaN and
    # are reported as unresolved so we can fix them, not silently misfile them.
}
POSITION_GROUPS = ["QB", "RB", "WR", "TE", "OT", "IOL", "EDGE", "IDL", "LB", "CB", "S"]


def to_pos_group(label):
    """Map a raw position label to a position group (NaN if unknown/excluded)."""
    if pd.isna(label):
        return None
    return POSITION_MAP.get(str(label).strip().upper())


# ---------- names (for matching players across sources) ----------
_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def clean_name(name) -> str:
    """Lowercase, strip accents, punctuation and suffixes: 'D.K. Metcalf Jr.' -> 'dk metcalf'."""
    if pd.isna(name):
        return ""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z\s]", "", s.lower())
    s = _SUFFIX.sub("", s)
    return re.sub(r"\s+", " ", s).strip()
