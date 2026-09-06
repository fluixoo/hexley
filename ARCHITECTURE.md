# Architecture

One process, six seats, one bus (a Python call chain today; the seats are pure functions over log lists, so swapping in a queue is a two-line change).

```
                 eth_getLogs x3 per range
  RPC  ───────►  TAP  ──── RangeResult ────►  DESK.ingest
                                                 │
                    ┌────────────────────────────┼────────────────────────┐
                    ▼                            ▼                        ▼
                DECODER                     GENEALOGIST               REFEREE
        curve words / v4 int128          crowd set (batch)        verdict rules (live)
        quote from same-tx transfer      union-find clusters      rule grid (batch)
                    │                            │                        │
                    └──────────► PROFILER ◄──────┘                        │
                           paths from copier fill                         │
                           scorecard                                      │
                                    └──────────────► CLERK ◄──────────────┘
                                             report · snapshot · verdict
```

## Data flow, live

1. `Tap.stream` polls `eth_blockNumber` every 250 ms and yields a `RangeResult` for every new span of blocks (max 80 per call). Three `eth_getLogs` per span: mints, curve buys, all transfers.
2. `Desk.ingest` registers launches (mint of exactly `1e27` to the curve), decodes buys, builds the buyer set from `Transfer(curve -> wallet)`, checks the crowd set, re-evaluates verdicts.
3. `Clerk.log` prints one line per event. Nothing is buffered, so a stall is visible immediately.

A failed range never stalls the stream: `Rpc.get_logs` splits on the node's 10k-match limit and on archive errors; if a span still fails, `Tap.stream` skips half of it and moves on.

## Data flow, batch

1. `Tap.wallet_transfers` pulls every ERC-20 transfer touching a wallet (both topic positions, 100k-block chunks, halving on error).
2. For each token the first buy is the leader's entry. The *next* trade on the same token after his is the copier's entry; the ratio of the two fills is the copier premium.
3. Minute candles from the token's pool give a normalized path from the copier's fill. `Profiler.score` turns the paths into the scorecard.
4. `Referee.grid` precomputes per path the first minute each level is touched (up, down, trailing). A rule resolves in O(1) per path, so the full grid is seconds, not hours.
5. `Referee.delay_cliff` re-bases every path to the price N minutes after the signal and re-runs the best rule. This is what a slow copier actually gets.
6. `Genealogist.cluster` links early buyers that co-enter within 30 blocks on 4+ launches. The cluster containing the leader is the crowd set used live.

## Why these boundaries

- **TAP is the only seat with network access for data.** Everything downstream is testable with fixtures.
- **DECODER has no state.** Sign conventions and decimals are the things that silently break; keeping them in pure functions keeps them under tests.
- **REFEREE never sees wallets, GENEALOGIST never sees prices.** They cannot leak assumptions into each other.
- **CLERK produces the only human-facing text**, so the verdict wording lives in one place.

## What is deliberately not here

- order routing, wallets, keys
- a database (JSON snapshots are enough at this size)
- a scheduler (cron the CLI)
