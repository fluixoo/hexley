"""DECODER: receipts in, signed amounts out.

Two sources of truth for a trade on this chain:
  * bonding curve BUY / SELL events (unsigned words: quote, tokens, fee)
  * Uniswap v4 PoolManager Swap events (int128 amounts, negative = user paid)

The quote token of a curve trade is not in the event. We read it from the
USDG / WETH Transfer that sits in the same transaction; if neither is there,
the buy was paid in native ETH and the raw size settles the guess.
"""

from __future__ import annotations

from collections import defaultdict

from .. import constants as C
from .. import decode as D
from ..models import Receipt


class Decoder:
    def __init__(self) -> None:
        self.decoded = 0
        self.rejected = 0

    @staticmethod
    def quote_by_tx(transfers: list[dict]) -> dict[str, str]:
        """tx hash -> 'USDG' | 'ETH' from quote-token transfers inside the tx."""
        q: dict[str, str] = {}
        for t in transfers:
            addr = t["address"].lower()
            if addr == C.USDG:
                q[t["transactionHash"]] = "USDG"
            elif addr == C.WETH:
                q.setdefault(t["transactionHash"], "ETH")
        return q

    def decode_curve(self, log: dict, quote_hint: str | None = None) -> Receipt | None:
        topic = log["topics"][0]
        if topic not in (C.TOPIC_CURVE_BUY, C.TOPIC_CURVE_SELL):
            return None
        quote_raw, tokens_raw, fee_raw = D.decode_curve_trade(log["data"])
        quote = quote_hint or D.guess_quote(quote_raw)
        amt = D.quote_to_float(quote_raw, quote)
        if not D.sane_buy(amt, quote):
            self.rejected += 1
            return None
        self.decoded += 1
        return Receipt(
            tx=log["transactionHash"],
            block=int(log["blockNumber"], 16),
            kind="curve_buy" if topic == C.TOPIC_CURVE_BUY else "curve_sell",
            token=log["address"].lower(),
            quote=quote,
            quote_amount=amt,
            token_amount=tokens_raw / 1e18,
            fee=D.quote_to_float(fee_raw, quote),
            paid=topic == C.TOPIC_CURVE_BUY,
        )

    def decode_v4(self, log: dict, quote_is_token0: bool) -> Receipt:
        a0, a1, _sqrt, _liq = D.decode_v4_swap(log["data"])
        quote_amt, token_amt = (a0, a1) if quote_is_token0 else (a1, a0)
        self.decoded += 1
        return Receipt(
            tx=log["transactionHash"],
            block=int(log["blockNumber"], 16),
            kind="v4_swap",
            token=log["address"].lower(),
            quote="ETH",
            quote_amount=abs(quote_amt) / 1e18,
            token_amount=abs(token_amt) / 1e18,
            paid=quote_amt < 0,
        )

    def decode_range(self, buys: list[dict], transfers: list[dict]) -> list[Receipt]:
        q = self.quote_by_tx(transfers)
        out: list[Receipt] = []
        for lg in buys:
            r = self.decode_curve(lg, q.get(lg["transactionHash"]))
            if r:
                out.append(r)
        return out

    @staticmethod
    def sign_test(receipts: list[Receipt]) -> tuple[int, int]:
        """(buys where the user paid, total buys). Should be equal; the day it is
        not, the sign convention changed under you."""
        buys = [r for r in receipts if r.kind in ("curve_buy", "v4_swap") and r.paid]
        total = [r for r in receipts if r.kind in ("curve_buy", "v4_swap")]
        return len(buys), len(total)

    @staticmethod
    def volume_by_token(receipts: list[Receipt]) -> dict[str, dict[str, float]]:
        vol: dict[str, dict[str, float]] = defaultdict(lambda: {"USDG": 0.0, "ETH": 0.0})
        for r in receipts:
            vol[r.token][r.quote] += r.quote_amount
        return dict(vol)
