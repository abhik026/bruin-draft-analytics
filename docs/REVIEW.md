# Project review (Nov 24, 2026)

Everything marked VERIFIED was reproduced by rebuilding from live nflverse data.

## A. Bugs fixed in this version
1. **VERIFIED, high: NaN-key merge in `build_nfl_side`.** `combine` has ~1,500 rows with no `pfr_id`; pandas joins NaN to NaN, so the 10 picks with no `pfr_id` all received one tight end's combine row (77 in, 263 lb, 4.87) and `pos_combine = TE`, which made them TE (Chad Jones, Myron Rolle, Kyle Calloway...). Fixed (blank keys dropped, `validate=` on merges). This is why TE was 208 here vs 197 in notebook 02.
2. **VERIFIED, high: position label leakage.** `pos_group` took the players-table position first, which is where a player ENDED UP. 16% of players disagree with their combine label (OT to G, CB to S, DT to DE, OLB to LB). The 35 IDL-to-EDGE movers average +10 AV surplus. Now: combine, then draft table, then players table; `position_source` and `pos_group_nfl` kept for sensitivity checks. EDGE surplus fell from +3.4 to +1.2 AV, LB rose from 0.2 to 1.6. EDGE vs LB is a labelling artifact until you fix one rule.
3. **High (by code reading; needs the real CFBD pull to confirm): college join.** Negative `collegeAthleteId` (465 picks) counted as matches and blocked the name fallback; `has_college_stats` counted zero placeholder rows (the "OL 28%" trap Member D found, but the pipeline repeated it). Fixed; tests in `tests/`. NOT yet built: name+school fallback for the 44 players whose stats sit under another playerId.
4. Medium: 4 unresolved DBs added to overrides (CSV also lacked a trailing newline). FB now maps to None with an `is_fullback` flag. `pull_college` defaults pulled only 1 pre-draft season; now 3.
5. Notebooks 01, 03, 04, 05 were run on different master builds (55 vs 53 columns, 70 vs 0 unresolved positions, 3,263 vs 3,264 vs 3,320 rows), and nothing is pinned to a data snapshot. Notebook 01 still shows 0% college match. Notebook 04 builds EDGE=547/LB=177 from CFBD labels while the master has different counts, so the college audit describes groups that do not exist in the master. Rerun everything after this fix and use one position rule.
6. Notebook 03 says OT, EDGE, IDL "hold up on both metrics"; notebook 02 says no position qualifies. 03 uses mean(outcome / tier mean), which late tiers dominate. Use 02's method.

## B. Methodology problems
1. **The outcome decides the answer.** Position surplus, cross-validated, shrunk (n/(n+50)):

| Position | w_av, 2010-18 | Rookie-window starter seasons, 2013-22 |
|---|---|---|
| IOL | +3.6 | +0.35 |
| OT | +2.2 | +0.19 |
| IDL | +2.4 | -0.12 |
| EDGE | +1.0 | -0.17 |
| CB | -3.3 | +0.03 |
| S | -1.1 | +0.23 |
| QB | -0.1 | -0.25 |
| TE | -2.8 | +0.04 |

   Only IOL and OT are positive under both. EDGE, CB, S, TE flip or vanish. Do not publish a "best position" from AV alone.
2. **Career w_av is the wrong yardstick for a team decision.** A team keeps a player cheaply for ~4 seasons. `get_rookie_window_outcome()` (new, `outcome.py`) counts full-time-equivalent starter seasons in years 1-4 from snap counts: same length for every class (no censoring), Spearman 0.92 with w_av, flat 1.1-1.25 across 2013-2022. It adds 5 classes (2019-2022 become usable) and recency.
3. **Cell-level stars are mostly noise.** Positions differ overall (permutation p < 0.001), but with pre-draft labels 6 of 46 cells are starred versus ~3 expected by chance (p = 0.055). Report position main effects with shrinkage (`shrunk_position_effects`) and only claim tier-specific results with a model, not a 66-cell grid. Position offsets improve leave-one-class-out R2 from 0.319 to 0.327: real but small.
4. **Layer 2 has a timing problem.** CFBD has no defensive stats before 2016, OL has none at all, and AV needs classes through 2018. Defensive models would train on two classes. The rookie-window outcome (classes to 2022) plus ESPN fill is what makes Layer 2 feasible.
5. Layer 2 benchmark should be pick + position, not pick alone; judge each position by incremental out-of-fold lift.
6. Surplus uses a curve fit including the player's own outcome (small effect, 0.998 correlation) and means only; add median, P(hit), P(bust). Means are dominated by a few stars.

## C. Making it real-world useful
- **Headline output:** a 2x2 per position and slot window: expected surplus (with interval) vs predictability (incremental out-of-fold lift). "Target" = high and high.
- **Availability:** "draft QB at 18" only works if a good QB is on the board. Simulate with the pool of players taken at picks p to p+10.
- **Deliver the rank, not just the position:** score the 2027 class by predicted surplus at its likely slot. The 2026 draft is done, so backtest on it.
- **Position-adjusted trade chart** from the fitted curve.
- **Risk and cost:** report bust/hit rates; add second-contract value as a second metric; keep rookie-scale cost in the story (same across positions at a slot).
- **Era:** check whether 2019-22 positional values differ from 2010-18 using the rookie metric.
- Add CI (pytest), pin a data snapshot date, and keep one position rule in `utils.py`.
