# Robinhood Chain: field notes

Everything below was measured through the public RPC, not read from docs.

## Basics

| item | value | how measured |
|---|---|---|
| chain id | 4663 | `eth_chainId` |
| stack | Arbitrum Orbit, single sequencer, FCFS | block cadence + tx ordering |
| block time | 95 to 105 ms | timestamps over 1,000-block windows, repeatedly |
| public RPC | `https://rpc.mainnet.chain.robinhood.com` | |
| fallback | `https://robinhood-rpc.publicnode.com` | |
| CORS | open on both | browser fetch from a file:// page works |

## RPC limits you will hit

- **10,000 matches per `eth_getLogs`.** Error text: `logs matched by query exceeds limit of 10000`. Halve the range and retry; `Rpc.get_logs` does it for you down to 32 blocks.
- **Archive errors on some historical ranges.** Error text: `Archive requests are not supported`. Same treatment. They come and go.
- **publicnode rejects topic-only filters** (no `address`). Use it for `eth_call` / blocks / balances, never for wide log scans.
- **User-Agent matters.** The primary node answers 403 to a bare `Python-urllib` agent. Send anything else.
- Latency from Europe: p50 around 150 to 250 ms per call. A 900-block backfill with three filters per 150-block range is about 20 calls, 5 seconds.

## Wallet types you will see

- **EOA**: `eth_getCode` returns `0x`.
- **EIP-7702 delegated EOA**: code starts with `0xef0100` followed by the delegate address. The delegate seen on retail wallets here is `0xe6cae83b…555b`. These wallets sign like EOAs but execute like smart accounts.
- **ERC-4337 accounts**: transactions arrive from bundlers with a `0x4337…` vanity prefix. The `tx.from` is the bundler, not the user. For attribution, follow the token `Transfer`, not the tx sender.

## Native ETH vs WETH

Curve buys can be paid in native ETH (no WETH transfer in the tx), in WETH, or in USDG (6 decimals). The curve event does not name the quote. `Decoder.quote_by_tx` looks for a USDG or WETH transfer in the same tx; if neither exists the raw size disambiguates (a 6-decimal amount is below 1e12, an 18-decimal one is not).

## Price reference

ETH/USDG comes from the Uniswap v3 pool `0x52e65b17…71ca` via `slot0()`:

```
price = (sqrtPriceX96 / 2^96)^2 * 10^(18-6)
```

It tracked Dexscreener within a few dollars every time we checked.
