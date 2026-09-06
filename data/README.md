# Data

All files are real reads from Robinhood Chain via the public RPC, produced by the code in this repo or its direct ancestors. Nothing is synthetic.

| file | what | produced |
|---|---|---|
| `desk_snapshot.json` | leader scorecard, referee grid summary, delay cliff, bootstrap CI, decoder sample, measured lag rows | 2026-09-05 23:25 UTC |
| `leader_tokens_2026-09-05.csv` | one row per token the leader touched in the window: entry time, on curve or pool, graduated, copier max, 1 h high/low, 6 h close, minutes to x2/x3/x5, his realized multiple, hold, sells | 2026-09-05 |
| `genealogy.json` | co-entry clusters, top wallets, kinds, method | 2026-09-06 |

Addresses are public on-chain identifiers.
