# NFL Draft Position Value (Bruin Sports Analytics)

**Question:** At a given draft slot, which position offers the highest expected surplus value (NFL production above what that pick typically returns), after accounting for how well college data predicts NFL outcomes at that position?

- **Layer 1 (no ML):** historical surplus by position and pick tier.
- **Layer 2 (ML):** player-level predictions from college + combine data; must beat the "pick slot only" baseline.

## Setup (everyone, ~5 minutes)

```bash
git clone <repo-url> && cd bruin-draft-analytics
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.data.pull_all          # downloads NFL data (no key needed)
python -m src.data.build_master      # builds data/processed/master.parquet
jupyter lab
```

## How data works

Data files are **never committed** (see `.gitignore`). Everyone rebuilds them with scripts.

| Data | Who pulls it | How |
|---|---|---|
| NFL (draft, combine, players, contracts) | Everyone | `python -m src.data.pull_all` (free, no key, about a minute) |
| College (CFBD player stats, draft picks) | **Member D, once** | Needs a free CFBD API key in `.env`. Run `python -m src.data.pull_college`, zip `data/raw/college/`, upload to the team Drive. Everyone else downloads it and unzips into `data/raw/college/`. No key needed for the rest of us. |
| Master table | Everyone | `python -m src.data.build_master` (rebuilds from raw) |

The free CFBD tier has a monthly call limit, which is why only one person pulls. If you re-pull, use `--force` deliberately.

## Who owns what

| Member | Notebook | Code you own |
|---|---|---|
| A: ______ (pipeline) | `01_master_table_a` | `src/utils.py`, `src/data/pull_nfl.py`, `pull_all.py`, `build_master.py` |
| B: ______ (draft value) | `02_draft_value_b` | `src/features/baseline.py` |
| C: ______ (outcome metric) | `03_outcome_metric_c` | `src/features/outcome.py` |
| D: ______ (college) | `04_college_production_d` | `src/data/pull_college.py`, `reports/college_feature_audit.md` |
| E: ______ (combine + IDs) | `05_combine_e` | `src/features/combine.py` |

Your task checklist is the first cell of your notebook and in `docs/week1_tasks.md`.

## Working rules

- `main` is protected: work on `eda/<topic>-<initial>` (e.g. `eda/draft-value-b`), open a PR, one teammate reviews.
- One owner per notebook. Do not edit someone else's notebook.
- Reusable logic goes in `src/`. Shared definitions (positions, class window, pick tiers) live only in `src/utils.py`.
- No API keys or data files in git, ever.

## Already verified (Nov 2026)

- `car_av` is empty in nflverse `draft_picks`; there is no per-season AV. The outcome is provisionally `w_av` (see `src/features/outcome.py`).
- Combine links to draft picks by PFR id (about 85% of 2010-2022 draftees have a combine row).
- Draft-table positions are coarse (DB, DE, OL); `build_master.py` refines them using the players and combine tables.
