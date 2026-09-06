# Co-entry clusters · 2026-09-06

Method: first 20 curve buys per launch across 115 launches, senders resolved via `eth_getTransactionByHash`, bundlers excluded, pair linked when both entries fall within 30 blocks, cluster when a pair shares 4+ launches. Source: [`data/genealogy.json`](../../data/genealogy.json).

| | |
|---|---|
| launches | 115 |
| early buyers | 1,095 |
| wallets kind-checked via `eth_getCode` | 120 |
| clusters | 6 |

## Cluster #1 (the crowd set)

22 wallets: 19 EOA, 3 EIP-7702. Contains the leader `0x5fa5…4cfb`, the linked wallet `0xf88f…2e17`, and the GMGN copier `0xd11c…`. Up to 42 shared launches inside a pair.

This is the set the live desk fires on. It is small on purpose; the moment it grows past a few dozen wallets it fires on every launch and the verdict stops meaning anything.

## Other clusters

| # | wallets | shared launches |
|---|---|---|
| 2 | 5 | 4 |
| 3 | 4 | 11 |
| 4 | 4 | 7 |
| 5 | 3 | 11 |
| 6 | 3 | 4 |

Clusters 2 to 6 are not linked to the leader and are not used live.
