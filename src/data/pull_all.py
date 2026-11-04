"""One command to get data: NFL always; college only if you have an API key.

    python -m src.data.pull_all
"""
import os

from dotenv import load_dotenv

from src.data.pull_nfl import pull_nfl
from src.utils import RAW_COLLEGE

if __name__ == "__main__":
    load_dotenv()
    pull_nfl()
    have_cache = any(RAW_COLLEGE.glob("*.parquet"))
    if have_cache:
        print("[ok] college data found in data/raw/college/")
    elif os.environ.get("CFBD_API_KEY"):
        from src.data.pull_college import pull_year
        from src.utils import CLASS_MAX, CLASS_MIN
        for yr in range(CLASS_MIN - 1, CLASS_MAX + 1):
            pull_year("player_stats", yr)
            pull_year("draft_picks", yr)
    else:
        print("[info] No college data yet. Download the shared college folder from the team "
              "Drive into data/raw/college/ (see README), or ask Member D.")
