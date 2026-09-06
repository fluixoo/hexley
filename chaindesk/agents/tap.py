"""TAP: the only seat that talks to the chain for raw data.

Three log filters per block range, fired together:
  mints      Transfer(0x0 -> *)           finds token births (filtered to 1e27)
  curve buys BUY topic                    finds trades on the bonding curves
  transfers  Transfer(*)                  per-block activity, leader hits, buyer set
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from .. import constants as C
from .. import decode as D
from ..models import Launch
from ..rpc import Rpc


@dataclass
class RangeResult:
    from_block: int
    to_block: int
    launches: list[Launch]
    buys: list[dict]
    transfers: list[dict]
    per_block: dict[int, dict] = field(default_factory=dict)

    @property
    def n_transfers(self) -> int:
        return len(self.transfers)


class Tap:
    def __init__(self, rpc: Rpc | None = None, leader: str | None = None) -> None:
        self.rpc = rpc or Rpc()
        self.leader_topic = D.address_to_topic(leader) if leader else None
        self._symbols: dict[str, str] = {}

    # ---- symbol lookup (cached) --------------------------------------------
    def symbol(self, token: str) -> str:
        if token in self._symbols:
            return self._symbols[token]
        try:
            raw = self.rpc.eth_call(token, C.SEL_SYMBOL)
            sym = D.clean_symbol(D.decode_string_return(raw))
        except Exception:
            sym = "?"
        self._symbols[token] = sym
        return sym

    # ---- one range -----------------------------------------------------------
    def scan_range(self, a: int, b: int, with_symbols: bool = True) -> RangeResult:
        mints = self.rpc.get_logs(a, b, topics=[C.TOPIC_TRANSFER, C.ZERO_TOPIC])
        buys = self.rpc.get_logs(a, b, topics=[C.TOPIC_CURVE_BUY])
        transfers = self.rpc.get_logs(a, b, topics=[C.TOPIC_TRANSFER])

        launches: list[Launch] = []
        for m in mints:
            if not D.is_launch_mint(m):
                continue
            token = m["address"].lower()
            curve = D.topic_to_address(m["topics"][2])
            launches.append(
                Launch(
                    token=token,
                    curve=curve,
                    block=int(m["blockNumber"], 16),
                    tx=m["transactionHash"],
                    symbol=self.symbol(token) if with_symbols else "?",
                )
            )

        per_block: dict[int, dict] = {}
        for t in transfers:
            k = int(t["blockNumber"], 16)
            o = per_block.setdefault(k, {"transfers": 0, "leader_hit": False, "launches": []})
            o["transfers"] += 1
            if self.leader_topic and (t["topics"][1] == self.leader_topic or t["topics"][2] == self.leader_topic):
                o["leader_hit"] = True
        for l in launches:
            per_block.setdefault(l.block, {"transfers": 0, "leader_hit": False, "launches": []})["launches"].append(l.symbol)
        return RangeResult(a, b, launches, buys, transfers, per_block)

    # ---- live stream --------------------------------------------------------
    def stream(self, poll_s: float = 0.25, max_batch: int = 80, start_block: int | None = None) -> Iterator[RangeResult]:
        """Yield RangeResults as the head advances. Never re-reads a block."""
        last = start_block if start_block is not None else self.rpc.block_number()
        while True:
            head = self.rpc.block_number()
            if head > last:
                a, b = last + 1, min(head, last + max_batch)
                try:
                    yield self.scan_range(a, b)
                    last = b
                except Exception:
                    # a bad range must not stall the stream; skip half of it and move on
                    last = a + (b - a) // 2
            time.sleep(poll_s)

    # ---- wallet history -----------------------------------------------------
    def wallet_transfers(self, wallet: str, from_block: int, to_block: int, chunk: int = 100_000) -> list[dict]:
        """Every ERC-20 Transfer touching the wallet, both directions, deduped."""
        topic = D.address_to_topic(wallet)
        seen: dict[str, dict] = {}
        for topics in ([C.TOPIC_TRANSFER, topic], [C.TOPIC_TRANSFER, None, topic]):
            for lg in self.rpc.iter_logs(from_block, to_block, chunk=chunk, topics=topics):
                seen[lg["transactionHash"] + lg["logIndex"]] = lg
        return sorted(seen.values(), key=lambda lg: (int(lg["blockNumber"], 16), int(lg["logIndex"], 16)))

    # ---- market data --------------------------------------------------------
    def eth_price_usdg(self) -> float:
        raw = self.rpc.eth_call(C.ETH_USDG_POOL_V3, C.SEL_SLOT0)
        return D.slot0_to_price(D.word(raw, 0))

    def block_time_ms(self, sample: int = 1000) -> float:
        head = self.rpc.block_number()
        t1 = int(self.rpc.get_block(head)["timestamp"], 16)
        t0 = int(self.rpc.get_block(head - sample)["timestamp"], 16)
        return 1000.0 * (t1 - t0) / sample
