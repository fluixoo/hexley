# Leader scorecard · 0x5fa57fcaf86e137cb8185c4cb2c01ea7b5b14cfb

computed 2026-09-05 23:25 UTC · window 2026-08-29 15:55 to 2026-09-05 23:03 UTC · blocks 49,277,601 to 55,498,401

Source data: [`data/desk_snapshot.json`](../../data/desk_snapshot.json), per-token rows in [`data/leader_tokens_2026-09-05.csv`](../../data/leader_tokens_2026-09-05.csv).

## Sample

| | |
|---|---|
| transfers | 588 |
| tokens | 156 |
| entries scored | 147 (115 on curve, 32 on pool) |
| graduated | 64 |

## Price after the copier's entry

| metric | value |
|---|---|
| p(x1.5) | 0.585 |
| p(x2) | 0.422 |
| p(x3) | 0.272 |
| p(x5) | 0.122 |
| p(x10) | 0.041 |
| median max | 1.76x |
| median low, first hour | 0.68x |
| median close, 6 h | 0.65x |
| copier premium | 1.081 |
| leader median hold | 3.2 min |
| leader win rate | 32% |
| leader median realized | 0.89x |

## Exit rules, top of the grid (852,096 combinations)

| # | rule | EV | win | PF |
|---|---|---|---|---|
| 1 | 100% @ x4 · time stop 60 m | +31.4% | 30% | |
| 2 | 100% @ x4 · time stop 30 m | +30.4% | 29% | |
| 3 | 100% @ x5 · stop 0.6 · 360 m · trail 40% | +27.3% | 41% | 3.18 |
| 4 | 100% @ x4 · 360 m · trail 15% | +19.2% | 57% | |

Rule A (100% @ x4, time stop 15 m): EV +29%, bootstrap 90% CI +14.6% to +45.4%.

Stops at entry: within noise. Best EV with no stop and with a 40% stop differ by less than the CI width.

## Delay cliff, rule A

| delay | EV |
|---|---|
| 0.1 s | +29.0% |
| 1 s | +15.3% |
| 3 s | +10.5% |
| 5 s | +6.5% |
| 15 s | +7.6% |
| 60 s | -6.3% |

## Verdict

fix routing before sizing up. no size until measured lag is 5 blocks or fewer on 7 straight days. re-score weekly, drop the leader if p(x2) falls under 0.35.

paper only.
