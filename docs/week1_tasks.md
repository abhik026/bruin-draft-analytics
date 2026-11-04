# Week 1 EDA: who does what

Full detail is in the project plan doc. Tick boxes as you go; every PR needs a notebook plus the three-part summary from the PR template.

## Member A: Pipeline lead
Notebook: `notebooks/01_master_table_a.ipynb`

- [ ] Run `python -m src.data.pull_all` then `python -m src.data.build_master`.
- [ ] Merge college stats into `build_master.py`. Join key idea: CFBD `/draft/picks` gives college athlete id + overall pick, so match on **(season, overall pick)** instead of fuzzy names. Verify the fields on the first real pull.
- [ ] Report college match rate by position group and draft year; list unmatched players.
- [ ] Resolve the ~36 players with unresolved positions (mostly `DB`).

## Member B: Draft value
Notebook: `notebooks/02_draft_value_b.ipynb`

- [ ] Plot raw mean outcome by pick, then the smoothed baseline (`fit_baseline`). Tune `frac` and justify it.
- [ ] Position x pick-tier table of mean surplus with n and bootstrap CIs. Many cells are tiny (see counts): grey them out or merge tiers.
- [ ] Heatmap. Answer: where does the curve flatten? Which positions beat their slot per tier?
- [ ] Check the baseline on a held-out set of classes.

## Member C: Outcome metric
Notebook: `notebooks/03_outcome_metric_c.ipynb`

- [ ] `car_av` is empty and there is no per-season AV. Decide how to handle `w_av` (career-length bias across classes): restrict window, divide by seasons possible, or use `dr_av` as a robustness check.
- [ ] AV by position: distribution, zero share, median, 90th percentile.
- [ ] Compare with `games` and `seasons_started`.
- [ ] Test contract value from `data/raw/nfl/contracts.parquet` as an alternative outcome.
- [ ] Update `src/features/outcome.py` with the final definition and post a recommendation.

## Member D: College production
Notebook: `notebooks/04_college_production_d.ipynb`

- [ ] Get a CFBD key, put it in `.env`, run `python -m src.data.pull_college --check` for coverage by season.
- [ ] Full pull, then zip `data/raw/college/` and upload to the team Drive.
- [ ] Per position group: available stats, coverage, missingness by year and school level.
- [ ] Write `reports/college_feature_audit.md`. Flag OL and other positions with almost no stats.

## Member E: Athletic testing and ID bridge
Notebook: `notebooks/05_combine_e.ipynb`

- [ ] Coverage of each test by position and year with `combine_coverage` (overall combine match is ~85%; 2021 is lower).
- [ ] Check position label consistency (EDGE vs LB vs DE, CB vs S) and look at weights.
- [ ] Improve the combine <-> draft join: PFR id first, then (draft_year, draft_ovr), then name. Report the match rate.
- [ ] After B's surplus lands: Spearman correlation of each test with surplus by position. Note who skips tests.

