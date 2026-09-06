# Dashboard

`index.html` is the whole desk in one file. Open it in a browser; it talks to `https://rpc.mainnet.chain.robinhood.com` directly (CORS is open) and needs no server, no build, no key.

What is live (badge `LIVE`, refreshed from the chain while the page is open):

- block stream, one row per block, transfer counts, LAUNCH and HIT flags
- launch radar: every token born in the last 900 blocks and since, with buys in the first 60 blocks, buyers, volume in the real quote token, crowd hits, score, verdict
- ETH/USDG from the v3 pool `slot0`, gas price, leader balance and nonce
- the six seats' counters and the operator log
- RPC call count, error count, p50 latency

What is a snapshot (badge `SNAPSHOT` with a `computed_at` stamp):

- leader scorecard, referee top rules, delay cliff, bootstrap CI
- measured copy lag rows (dated)

The two are kept visually separate on purpose. A live number and a backtest number should never sit in the same cell.

Fits any viewport by scaling a 1920×1080 stage. Rendered stills in the docs come from headless Edge with a virtual time budget so the network requests complete.

`make dashboard` serves it on `http://localhost:8787` if your browser blocks fetch from `file://`.
