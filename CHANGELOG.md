# Changelog

## 0.3.0 · 2026-09-06

- live desk: `chaindesk watch` with backfill, stream, verdicts, snapshot
- dashboard: single-file browser desk on the public RPC, block stream per block, launch radar, six seats, operator log
- decoder: quote detection from same-tx transfers, sanity guard on implausible sizes
- rpc: User-Agent header (the primary node 403s a bare urllib agent), getLogs never falls back to publicnode
- docs: chain notes, launchpad mechanics, methodology, dated results, one page per seat

## 0.2.0 · 2026-09-05

- referee: vectorized rule grid with precomputed first-hit indices, delay cliff, bootstrap CI
- profiler: scorecard from copier-fill paths, copier premium
- genealogist: union-find co-entry clustering, bundler exclusion, crowd set
- results: leader scorecard for `0x5fa5…4cfb`, 147 entries, 852,096 rules

## 0.1.0 · 2026-09-03

- tap: launch detection via `Transfer(0x0 -> curve)` of exactly 1e27, curve buy filter, wallet transfer scan
- rpc: range splitting on the 10k-match limit and archive errors
- decode: curve words, v4 int128 sign extension, string returns, 7702 code prefix
