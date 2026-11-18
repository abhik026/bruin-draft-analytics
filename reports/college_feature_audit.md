# College feature audit (Member D)

What college production data we have for drafted players, how complete it is by position, and which features are worth carrying into Layer 2. All numbers come from `notebooks/04_college_production_d.ipynb`.

## Summary

- **Offense is well covered.** QB/RB/WR/TE have relevant final-season stats for 82–94% of the 2010–16 classes and 92–97% of the 2017–22 classes.
- **OT and IOL have no usable college production.** Their models will have to rely on size, combine, and pick slot.
- **CFBD has no defensive stats (tackles, sacks, TFL, hurries, PD) before the 2016 season.** EDGE and IDL have 0% coverage for the 2010–16 draft classes. LB, CB, and S are covered only by interceptions for those classes. This is the biggest issue in the data. ESPN play-by-play data can partly fill it (sacks, PBU, INT, forced fumbles, but no tackles or TFL). See [Source feasibility check](#source-feasibility-check).
- **FCS and lower-division players are mostly missing** (50–88% by position), and the stats that do exist look partial.
- **Raw counting stats aren't comparable across school levels or seasons** (G5 totals run higher than Power, and 2020 was a short season). Recommendation: standardize within season × position, and add school level as its own feature.
- The team needs to make a few decisions before Layer 2. See [Known issues and open decisions](#known-issues-and-open-decisions).

## Data and definitions

- **Source:** CollegeFootballData (CFBD) season stats and draft picks, seasons 2008–2022, pulled with `src/data/pull_college.py` and cached in `data/raw/college/`.
- **Population:** draft classes 2010–2022 (`CLASS_MIN`/`CLASS_MAX`), 3,263 picks after excluding K/P/LS/KR/PR. Only drafted players are counted.
- **Join:** `picks.collegeAthleteId` = `stats.playerId`, pre-draft seasons only (`season < draft year`).
- **Zero placeholder rows:** if a player has any stat in a category, CFBD writes every stat in that category, mostly as 0. Coverage counts only nonzero values.
- **Relevant stats:** each position gets a list of stats chosen by football role (for example, sacks/TFL/hurries/tackles for EDGE). OT/IOL have none.
- **`rel_any`:** share of a position with at least one nonzero relevant stat in any pre-draft season.
- **`rel_final`:** share with one in the **final season**, defined as draft year − 1. A player who sat out his last year counts as missing (see open decisions).

## Coverage by position group

| Group | Drafted | rel_any | rel_final | rel_final, 2010–16 classes | rel_final, 2017–22 classes |
|---|---|---|---|---|---|
| QB | 150 | .933 | .927 | .917 | .939 |
| RB | 293 | .925 | .918 | .874 | .970 |
| WR | 412 | .908 | .891 | .844 | .943 |
| TE | 182 | .874 | .868 | .825 | .918 |
| OT | 263 | 0 | 0 | 0 | 0 |
| IOL | 285 | 0 | 0 | 0 | 0 |
| EDGE | 547 | .389 | .384 | **0** | .913 |
| IDL | 273 | .432 | .418 | **0** | .912 |
| LB | 177 | .927 | .842 | .696 | .959 |
| CB | 419 | .826 | .759 | .643 | .892 |
| S | 262 | .844 | .763 | .612 | .922 |

The 2016 class is grouped with the early classes because its final season (2015) came before CFBD added defensive stats.

## Flagged positions

**OT / IOL: no production.** A naive count says 28% of OT and 30% of IOL have stats. Almost all of those are about one tackle per season (after a turnover), plus the odd trick-play carry. These numbers are meaningless as features.

**EDGE / IDL: nothing before 2016.** I verified the gap three ways:
- the cached season stats
- the season-stats API (2013: 0 defensive rows)
- the box-score API (2013 week 5: 49 games, no defensive category)

For the 2010–16 classes, 0% of every defensive group has any `defensive.*` stat. Coverage is 91% for the 2017–22 classes.

**LB / CB / S: interceptions only before 2016.** Interceptions exist in every year, so these groups keep 61–70% early coverage. But for those classes, "covered" means "we know their INT count and nothing else." For LBs this is thin: the pre-2016 LBs with an interception have a median of 2 career INTs.

## Available stats per position

Availability among the 2017–22 classes (players with any stats), so the defensive gap doesn't hide which stats exist:

- **Every chosen relevant stat is present for at least 90% of its position**, except LB interceptions (78%, since many linebackers never record one).
- **Common stats not in the relevant lists that are worth adding:** QB `rushing.CAR` (100%), LB `defensive.QB HUR` (90%), CB `defensive.TFL` (93%), S `defensive.TFL` (98%).
- **Rate stats** (`passing.PCT`, `passing.YPA`, `rushing.YPC`, `receiving.YPR`) are in CFBD but can be computed from the counts, so they don't need separate handling.

## Missingness

### By draft class

Share of each position with **no** relevant stat in any pre-draft season (OT/IOL excluded, since they're 100% by definition):

| Group | 2010–16 | 2017–22 |
|---|---|---|
| QB | .08 | .05 |
| RB | .12 | .02 |
| WR | .14 | .04 |
| TE | .18 | .07 |
| EDGE | **1.00** | .07 |
| IDL | **1.00** | .06 |
| LB | .14 | .02 |
| CB | .27 | .07 |
| S | .27 | .04 |

For offense, the earliest classes are the worst: 15–28% missing for 2010–11, compared with 5–13% for 2012–16. Part of the reason is that the raw data starts in 2008, so the 2010–11 classes have the shortest pre-draft history. The year-by-year table is in the notebook. TE swings a lot year to year because each class is small.

### By school level

| Group | Power | G5/Ind | FCS/Other |
|---|---|---|---|
| QB | .03 | .03 | .60 |
| RB | .06 | .04 | .50 |
| WR | .03 | .05 | .77 |
| TE | .06 | .12 | .85 |
| EDGE | .59 | .57 | .85 |
| IDL | .53 | .58 | .88 |
| LB | .07 | .00 | .75 |
| CB | .09 | .10 | .81 |
| S | .09 | .14 | .86 |

- **FCS/Other is the clear problem.** It covers 279 picks in all, and some cells are tiny (4 LBs, 10 QBs).
- **Power and G5 are close.** The ~55–60% EDGE/IDL rate at both is the pre-2016 gap, not a school-level effect.
- Levels come from the draft record's `collegeConference`. Power is ACC, Big 12, Big Ten, SEC, Pac-12/Pac-10, and Big East. G5/Ind is the other FBS conferences plus FBS independents.

### Why players are missing

920 picks have no stats at all:
- **465 have a negative `collegeAthleteId`.** That's CFBD's marker for a pick that isn't linked to a college player record, so an ID join can never find them. All of them are Power or G5 players, mostly OL and DL.
- **44 have stats filed under a different `playerId`.** Examples are Rob Gronkowski and Jermaine Gresham. They're found by exact name + school, and 20 of them are in the 2010 class.
- **The remaining ~411** are mostly FCS/Other players and OL, who have no stats in CFBD.

These 44 are left unmatched in this audit. The ID join is clean when it hits, but the master table should fall back to name + school matching.

## Distributions

### Headline stat per position (final pre-draft season)

| Group | Stat | Players | 25th pct | Median | 75th pct |
|---|---|---|---|---|---|
| QB | passing yards | 139 | 2,848 | 3,316 | 3,895 |
| RB | rushing yards | 263 | 647 | 1,060 | 1,398 |
| WR | receiving yards | 367 | 676 | 913 | 1,180 |
| TE | receiving yards | 158 | 278 | 450 | 604 |
| EDGE | sacks | 210 | 3.5 | 5.5 | 8.5 |
| IDL | TFL | 114 | 5.0 | 7.8 | 11.4 |
| LB | total tackles | 94 | 65 | 85 | 104 |
| CB | passes defended | 174 | 4 | 7 | 10 |
| S | total tackles | 118 | 50 | 65 | 75 |

Real zeros are kept here (for example, an EDGE with tackles but no sacks). The top values were checked and are all real seasons: Melvin Gordon's 2,587 rushing yards in 2014, Joe Burrow's 2019, and Chase Young's 16.5 sacks. Nothing needs cleaning.

### School level

Median headline stat by level:

| Group | Power | G5/Ind | FCS/Other |
|---|---|---|---|
| QB | 3,187 | 3,555 | 224 |
| RB | 1,022 | 1,133 | 125 |
| WR | 866 | 1,117 | 138 |
| TE | 419 | 515 | 136 |
| EDGE | 5.75 | 6.5 | 0 |
| IDL | 7.5 | 10.5 | 1 |

- **Drafted G5 players have higher raw totals than Power players.** A likely explanation is that a G5 player has to dominate weaker opponents to get drafted, so 1,000 yards doesn't mean the same thing at each level. This hasn't been tested.
- **The level gap mostly disappears for a per-attempt stat.** QB passer efficiency is 152 at G5 and 150 at Power.
- **FCS medians are tiny** (QB 224 yards, EDGE 0 sacks). That suggests CFBD has only some of their games. It's based on 1–7 players per position, so FCS college stats should be treated as missing, not trusted.

### Season

Most positions are fairly stable from season to season, with noise from small groups (about 9–40 players per season and position). **2020, the COVID-shortened season, is the exception.**

| Group | Typical median (other seasons) | 2020 median |
|---|---|---|
| RB | 1,085 | 858 |
| WR | 927 | 625 |
| TE | 475 | 294 |
| IDL | 8.5 | 4.5 |
| CB | 8.5 | 4.0 |
| S | 68.5 | 42.0 |

QB, EDGE, and LB dropped less.

### Recommendation

CFBD season stats have no games-played column, so counting stats can't be turned into per-game rates. Instead:
1. **Standardize each stat within season × position**, for example with a percentile or z-score among that year's drafted players at the position. This removes both era drift and the 2020 dip.
2. **Add school level** (Power / G5 / FCS) as its own feature.
3. **Treat FCS/Other college stats as missing.**
4. **Prefer per-attempt stats where they exist** (passer efficiency, YPC, YPR). They're less tilted by level and by games played.

## Candidate features

Every position group also gets **school level, combine and size measurements, and pick slot**, standardized as above. These are candidates to test against the pick-slot-only baseline in Layer 2, not a final list.

| Group | Final-season stats | Career stats | Coverage (2010–16 / 2017–22) | Main concern |
|---|---|---|---|---|
| QB | passing ATT/YDS/TD/INT, passer efficiency, rushing CAR/YDS | career pass YDS/TD, seasons with stats | .92 / .94 | small group (~150); efficiency noisy under 100 attempts |
| RB | rushing CAR/YDS/TD, receiving REC/YDS, YPC | career rush YDS, career REC | .87 / .97 | counting stats favor durable players |
| WR | receiving REC/YDS/TD, YPR | career rec YDS/TD | .84 / .94 | counting stats favor durable players |
| TE | receiving REC/YDS/TD, YPR | career rec YDS/TD | .82 / .92 | small classes; blocking TEs have few catches |
| OT | none | none | 0 / 0 | size, combine, pick slot only |
| IOL | none | none | 0 / 0 | size, combine, pick slot only |
| EDGE | SACKS, TFL, QB HUR, TOT | career SACKS/TFL (2017+ classes) | 0 / .91 | no defensive stats before 2016; OLB→EDGE mapping inflates group |
| IDL | TFL, SACKS, QB HUR, TOT | career TFL/SACKS (2017+ classes) | 0 / .91 | no defensive stats before 2016 |
| LB | TOT, SOLO, TFL, SACKS, QB HUR, PD, INT | career TOT/TFL (2017+), career INT (all) | .70 / .96 | pre-2016 classes covered by INTs only |
| CB | PD, INT, TOT, SOLO, TFL | career PD (2017+), career INT (all) | .64 / .89 | pre-2016 classes covered by INTs only |
| S | PD, INT, TOT, SOLO, TFL | career TOT/PD (2017+), career INT (all) | .61 / .92 | pre-2016 classes covered by INTs only |

**Passer efficiency** is the NCAA formula, computed from final-season counts:

```
(8.4 × YDS + 330 × TD + 100 × COMPLETIONS − 200 × INT) / ATT
```

QBs with fewer than 100 attempts are set to missing. 135 of 139 QBs qualify, and the median is 150.5. As a check, Joe Burrow's 2019 comes out at 202.0, which matches his official rating.

Career totals are short for the 2010–11 classes, since the data starts with the 2008 season. Like final-season counts, they favor durable players.

## Known issues and open decisions

### Known issues

1. **Pre-2016 defensive gap** (biggest). There are no tackles, sacks, TFL, hurries, PD, or fumbles before the 2016 season. Interceptions exist in all years.
2. **Zero placeholder rows.** Counting rows without filtering `value > 0` inflates coverage. This is the OL 28% trap.
3. **OLB→EDGE mapping.** `POSITION_MAP` sends OLBs to EDGE (547 EDGE vs. 177 LB). A weight or sack-rate split may be needed. Rehan and Gonzalo's call.
4. **3 "Defensive Back" picks** were hand-assigned to CB/S by NFL roster position.
5. **No games-played column**, so there are no per-game rates, and counting stats favor durable players.
6. **Final-season definition.** Draft year − 1, not "last season played."
7. **Short pre-draft history for the 2010–11 classes** (data starts in 2008).
8. **Pac-10 label.** The conference's pre-2011 name has to be listed as Power, or 59 picks from the 2010–11 classes get labeled FCS/Other. Fixed in the notebook.
9. **ID mismatches.** 465 picks have unlinked (negative) IDs, and 44 have stats under a different `playerId`.
10. **FCS coverage looks partial.**
11. **2020 short season** depresses counting stats.

### Decisions for the team

1. **Pre-2016 defenders.** Options:
   - (a) fit defensive Layer 2 models on the 2017–22 classes only
   - (b) use combine and pick slot only for earlier defenders
   - (c) add ESPN play-by-play defensive events (sacks, PBU, INT, FF; no tackles or TFL) from sportsdataverse. Validated against CFBD, and it covers 91–96% of early defenders. See the feasibility check below.
2. **OLB→EDGE split**, before EDGE results are interpreted.
3. **Final season:** keep draft year − 1, or switch to the last season played.
4. **FCS players:** treat their college stats as missing (recommended), or keep them with a level flag.
5. **Master table matching:** add a name + school fallback after the ID join.

## Source feasibility check

Can another source fill the pre-2016 defensive gap? The checks are in the notebook section "Pre-2016 defensive fill (ESPN play-by-play)".

### Ruled out

- **Sports Reference (College Football Reference).** Its terms prohibit automated access ("scripts, bots, scrapers, data miners") and using its content for "supporting machine learning methods used to predict, classify, label, or score inputs into the models." Layer 2 is exactly that, so it can't be used without written permission.
- **cfbfastR's `cfbd_*` functions.** They wrap the same CFBD API we already use, so they have the same gap.
- **ESPN box scores** (cfbfastR `load_espn_cfb_player_box`). These have no defensive category in 2013 but do in 2018, so they have the same gap. CFBD likely sources its box scores from ESPN.

### Usable: ESPN play-by-play defensive events

sportsdataverse (the project behind cfbfastR) publishes `espn_cfb_adv_defensive_players`: per-player, per-game counts of **sacks, pass breakups, interceptions, and forced fumbles**, parsed from ESPN play-by-play text. It covers 2004 onward, as parquet files read directly with pandas (no R needed).

**What it lacks:**
- **No tackles before 2014, and no TFL or QB hurries in any year.** (A separate `espn_cfb_adv_tackles` release covers tackles from 2014 on.)
- **2013 sacks are broken:** 18 in the whole season, compared with about 3,000–3,500 in the seasons around it. Pass breakups and forced fumbles look normal in 2013. 2013 is the final season for the 2014 class.
- **No player ID.** Players are matched by school (`picks.collegeId` is ESPN's team id) plus last name + first initial. Exact names miss nicknames (Chris/Christopher) and some names carry junk team prefixes. 20 drafted defenders share a school + key with another pick, so a few matches could be wrong.

**Validation.** For 2016–17, where CFBD has defense, ESPN and CFBD sacks for the same 725 drafted player-seasons agree exactly 78% of the time and are within one sack 97% of the time. The correlation is 0.96, and the average difference is about 0. That's slightly noisy but not biased.

**Coverage for the 2010–16 classes** (share with an ESPN row in any pre-draft season / in the final season):

| Group | Any season | Final season | Before the fill (`def_any`) |
|---|---|---|---|
| EDGE | .956 | .899 | 0 |
| IDL | .912 | .845 | 0 |
| LB | .962 | .949 | 0 |
| CB | .960 | .884 | 0 |
| S | .948 | .896 | 0 |

- **Power and G5 defenders match 99% of the time. FCS/Other only matches 57%** (93 players).
- **The 2014 class is the weak spot:** 73% final-season coverage, and its final-season sacks are unusable.
- **Spot checks look right:** Suh 2009 (12.5 sacks), Von Miller 2009 (16), Clowney 2012 (14).

**License.** The sportsdataverse data repo is MIT-licensed for code, and its README marks the data CC BY 4.0, which requires attribution. The underlying data comes from ESPN, and ESPN's own terms haven't been reviewed. Someone should check them before this goes into the final pipeline.

### Recommendation

This source makes option (c) realistic for **sacks, pass breakups, INTs, and forced fumbles** for the 2010–16 classes (except 2013 sacks). It does **not** recover tackles or TFL. If the team adopts it:
- Pre-2016 defensive features would be a smaller set than post-2016 ones (sacks, PBU, INT, FF), so models should only use those four stats across all years, or fit the eras separately.
- 2013 sacks should be set to missing, not 0.
- The pull would go into `src/data/pull_college.py` as a cached download, and the matching logic would go into `src/`.

Source: [sportsdataverse-data](https://github.com/sportsdataverse/sportsdataverse-data), release `espn_cfb_adv_defensive_players` (CC BY 4.0).
