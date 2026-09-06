# The six seats

| seat | module | inputs | outputs | network |
|---|---|---|---|---|
| TAP | `chaindesk/agents/tap.py` | block range | `RangeResult` (launches, buys, transfers, per-block) | yes |
| DECODER | `chaindesk/agents/decoder.py` | logs | `Receipt` (signed quote/token amounts) | no |
| GENEALOGIST | `chaindesk/agents/genealogist.py` | early buyers per launch | `Cluster` list, crowd set | no (kinds via `eth_getCode` optional) |
| PROFILER | `chaindesk/agents/profiler.py` | normalized paths | `Scorecard` | no |
| REFEREE | `chaindesk/agents/referee.py` | normalized paths | `RuleResult` list, delay cliff, CI | no |
| CLERK | `chaindesk/agents/clerk.py` | all of the above | markdown, json, verdict | no |

## TAP

Three filters per span, all `eth_getLogs`:

1. `[Transfer, 0x0]` mints, filtered to `data == 1e27`
2. `[CURVE_BUY]`
3. `[Transfer]` everything, for per-block counts, buyer sets and leader hits

`stream()` never re-reads a block and never blocks on a failed range. `wallet_transfers()` scans both topic positions in 100k-block chunks.

## DECODER

Curve events carry no quote token. Resolution order: USDG transfer in the same tx, else WETH transfer, else size heuristic. Buys above 200 ETH or 2M USDG are rejected as mis-detected and counted in `decoder.rejected`, never in volume.

`sign_test()` returns `(paid, total)` for buys. They must match; the first time they do not, stop and look.

## GENEALOGIST

Union-find over pairs. Excludes the router and any `0x4337…` sender. `crowd_set(clusters, anchor)` returns the anchor's cluster, which is what the live desk uses.

## PROFILER

Paths are `price / entry_price` per minute from the copier fill. `score()` returns the scorecard; `bootstrap()` gives a CI on any statistic.

## REFEREE

Precomputed first-hit indices, O(1) per rule per path. Default grid: 7 TP levels × 2 fractions × 4 stops × 5 time stops × 4 trails = 1,120 rules; the published run used a finer grid (852,096). `delay_cliff()` re-bases paths N minutes late.

## CLERK

`verdict()` compares the measured copy lag against the delay cliff and emits one of three sentences: do not copy / fix routing before sizing up / inside the cliff, paper size only. `report()` writes the markdown you see in `docs/results/`.
