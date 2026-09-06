# Methodology

## Entries

For a wallet W and a token T, the leader entry is W's first inbound `Transfer` of T. The copier entry is the first trade on T by any other wallet *after* the leader's block. The copier premium is `copier_fill / leader_fill`; the median across the leader dataset is 1.08.

Everything downstream is measured from the **copier** fill. Scoring from the leader's own fill would flatter every result by the premium.

## Paths

Minute OHLCV from the token's pool (curve or v4) starting at the copier's minute, normalized to 1.0 at entry, capped at 6 hours. Missing minutes are forward-filled. Tokens with fewer than 5 minutes of data are dropped (9 of 156 in the leader dataset).

## Scorecard

| metric | definition |
|---|---|
| p(xK) | share of entries whose path max reached K |
| median max | median of path maxima |
| median low 1h | median of path minima in the first 60 minutes |
| median close 6h | median of the path value at minute 360 |
| hold | leader's own median time from first buy to last sell |
| his win rate | share of the leader's own round-trips that closed above 1.0 |

## Rule grid

A rule is `(tp, tp_frac, stop, time_stop, trail)`. The referee precomputes per path:

- first minute `>= tp`
- first minute `<= stop`
- first minute `<= running_max * (1 - trail)`

and resolves each leg in O(1). The published grid ran 852,096 combinations in 80 seconds on a laptop. EV is the mean return per entry, equal size per entry, no fees (fees on this launchpad are around 1% each way; subtract 2 points from every EV to be safe).

## Delay cliff

Re-base every path to the price N minutes after the signal, run the same rule. This is not a simulation of slippage; it is exactly the fill a copier gets when it lands N minutes late. Sub-minute delays use the first-minute candle's open/high interpolation, which is optimistic, so treat the 0.1 s and 1 s rows as upper bounds.

## Confidence

Bootstrap over entries (2,000 resamples) for the 90% interval. With 147 entries the interval on the best rule is wide (+14.6% to +45.4%). That width is the honest answer; do not size on the point estimate.

## Measured copy lag

For three launches on 2026-09-05 we recorded the block of the leader's fill and the block of known copier routes' fills on the same token:

| route | lag, blocks |
|---|---|
| leader (3 wallets, same cluster) | 0 |
| GMGN copy wallet `0xd11c…` | +1 / +4 / +1 |
| Telegram bot user | +5 / +7 / +10 |

One block is 100 ms. Cross this with the delay cliff before believing any EV.
