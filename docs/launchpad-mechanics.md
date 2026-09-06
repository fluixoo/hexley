# Launchpad mechanics, as seen in raw logs

## A token is born

One transaction, one `Transfer` log:

```
topics[0]  Transfer
topics[1]  0x000…000            (mint)
topics[2]  <bonding curve address>
data       0x…0000033b2e3c9fd0803ce8000000   = 1_000_000_000 * 1e18 = 1e27
```

That single line identifies a launchpad token with no false positives we have found in 6 days of scanning. ERC-721 mints share the topic but carry an empty `data` field, so the length check in `decode.is_launch_mint` removes them.

The token contract's `symbol()` is read once and cached.

## Trades on the curve

The curve contract emits two events with the same layout:

| event | topic | word0 | word1 | word2 |
|---|---|---|---|---|
| BUY | `0xec36bf57…c455` | quote in | tokens out | fee |
| SELL | `0x8113d738…59df` | tokens in | quote out | fee |

Each BUY comes with a `Transfer(curve -> buyer)` of the token in the same tx. That transfer is how the desk attributes the buy to a wallet, because the tx sender is often a router or a bundler.

The router `0x65050a9b…40dc` shows up as an intermediate holder and is excluded from buyer sets.

## Graduation

When the curve fills, liquidity moves to a Uniswap v4 pool under the PoolManager `0x8366a39c…0951`. From there trades are `Swap` events with int128 amounts packed into 32-byte words. Negative amount means the user paid that side. `decode.decode_v4_swap` sign-extends at 256 bits, which is what the encoding actually is (a naive int128 read is wrong on this chain).

In the leader dataset 64 of 156 tokens graduated.

## Activity levels (measured)

- launches: 15 to 30 per minute during EU/US hours
- curve buys: 1,500 per 2,000 blocks (200 s) is a normal reading
- early buyers across 115 launches: 1,095 distinct wallets

That density is why a 60-block (6-second) window is enough to score a launch.
