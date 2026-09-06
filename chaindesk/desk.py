"""The desk: wires the six seats into one live loop.

    tap -> decoder -> (genealogist crowd set) -> profiler score -> referee verdict -> clerk

Verdict rules (paper, no orders):
    FIRE   a crowd wallet bought, or >= 12 buys and >= 8 distinct buyers inside 60 blocks
    WATCH  >= 6 buys inside 60 blocks
    PASS   otherwise
    closed 300 blocks after launch unless it fired
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import constants as C
from . import decode as D
from .agents import Clerk, Decoder, Tap
from .models import Launch
from .rpc import Rpc


@dataclass
class DeskConfig:
    leader: str | None = None
    crowd: set[str] = field(default_factory=set)
    backfill_blocks: int = 900
    close_after_blocks: int = 300
    fire_buys: int = 12
    fire_buyers: int = 8
    watch_buys: int = 6
    poll_s: float = 0.25

    @classmethod
    def from_toml(cls, path: str | Path) -> DeskConfig:
        import tomllib

        raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        d = raw.get("desk", {})
        return cls(
            leader=(d.get("leader") or None),
            crowd={a.lower() for a in d.get("crowd", [])},
            backfill_blocks=int(d.get("backfill_blocks", 900)),
            close_after_blocks=int(d.get("close_after_blocks", 300)),
            fire_buys=int(d.get("fire_buys", 12)),
            fire_buyers=int(d.get("fire_buyers", 8)),
            watch_buys=int(d.get("watch_buys", 6)),
            poll_s=float(d.get("poll_s", 0.25)),
        )


class Desk:
    def __init__(self, cfg: DeskConfig | None = None, rpc: Rpc | None = None) -> None:
        self.cfg = cfg or DeskConfig()
        self.rpc = rpc or Rpc()
        self.tap = Tap(self.rpc, leader=self.cfg.leader)
        self.decoder = Decoder()
        self.clerk = Clerk()
        self.launches: dict[str, Launch] = {}  # curve address -> launch
        self.head = 0
        self.counters = {"launches": 0, "buys": 0, "buyers": 0, "fire": 0, "watch": 0, "pass": 0, "crowd_hits": 0}

    # ---- scoring ------------------------------------------------------------
    def score(self, l: Launch) -> int:
        return min(100, l.buys_first_60 * 3 + len(l.buyers) * 5 + len(l.crowd) * 25 + (10 if l.volume > 0.5 else 0))

    def verdict(self, l: Launch) -> tuple[str, str]:
        if l.crowd:
            return "fire", f"crowd wallet {next(iter(l.crowd))[:6]}… entered"
        if l.buys_first_60 >= self.cfg.fire_buys and len(l.buyers) >= self.cfg.fire_buyers:
            return "fire", f"{l.buys_first_60} buys · {len(l.buyers)} buyers inside 60 blk"
        if l.buys_first_60 >= self.cfg.watch_buys:
            return "watch", f"{l.buys_first_60} buys · {len(l.buyers)} buyers · need {self.cfg.fire_buys}/{self.cfg.fire_buyers}"
        return "pass", f"{l.buys_first_60} buys · {len(l.buyers)} buyers"

    # ---- ingest one range ---------------------------------------------------
    def ingest(self, rr, live: bool = True) -> None:
        self.head = max(self.head, rr.to_block)
        for l in rr.launches:
            if l.curve not in self.launches:
                self.launches[l.curve] = l
                self.counters["launches"] += 1
                if live:
                    self.clerk.log("tap", f"launch detected · ${l.symbol} · curve {l.curve[:10]}… · blk {l.block:,}")
        quote = self.decoder.quote_by_tx(rr.transfers)
        for lg in rr.buys:
            l = self.launches.get(lg["address"].lower())
            if not l:
                continue
            r = self.decoder.decode_curve(lg, quote.get(lg["transactionHash"]))
            if not r:
                continue
            l.quote = r.quote
            l.volume += r.quote_amount
            l.buys += 1
            if r.block - l.block <= 60:
                l.buys_first_60 += 1
            self.counters["buys"] += 1
        tracked = set(self.launches)
        for t in rr.transfers:
            frm, to = D.topic_to_address(t["topics"][1]), D.topic_to_address(t["topics"][2])
            if frm in tracked and to not in tracked and to != C.LAUNCHPAD_ROUTER:
                l = self.launches[frm]
                if to not in l.buyers:
                    l.buyers.add(to)
                    self.counters["buyers"] += 1
                if to in self.cfg.crowd and to not in l.crowd:
                    l.crowd.add(to)
                    self.counters["crowd_hits"] += 1
                    if live:
                        self.clerk.log("genealogist", f"crowd wallet {to[:10]}… entered ${l.symbol}")
        for l in self.launches.values():
            if l.verdict == "closed":
                continue
            v, why = self.verdict(l)
            if v != l.verdict:
                if live and v in ("fire", "watch"):
                    self.clerk.log("referee", f"{v.upper()} ${l.symbol} · {why} · score {self.score(l)}")
                l.verdict, l.why = v, why
            if l.age(self.head) > self.cfg.close_after_blocks and l.verdict != "fire":
                l.verdict = "closed"

    # ---- run ----------------------------------------------------------------
    def backfill(self) -> None:
        head = self.rpc.block_number()
        a = head - self.cfg.backfill_blocks
        self.clerk.log("hexley", f"backfill {self.cfg.backfill_blocks} blocks · {a:,}..{head:,}")
        for s in range(a, head + 1, 150):
            e = min(s + 149, head)
            try:
                self.ingest(self.tap.scan_range(s, e), live=False)
            except Exception as ex:  # a failed range is logged and skipped, never fatal
                self.clerk.log("bus", f"range {s:,}..{e:,} skipped: {str(ex)[:60]}")
        self.head = head
        self.clerk.log("hexley", f"backfill done · {len(self.launches)} launches · {self.counters['buys']} buys · now streaming")

    def run(self, blocks: int | None = None) -> None:
        self.backfill()
        start = self.head
        for rr in self.tap.stream(poll_s=self.cfg.poll_s, start_block=self.head):
            self.ingest(rr, live=True)
            if blocks is not None and self.head - start >= blocks:
                break
        self.clerk.log("hexley", f"stopped at block {self.head:,} · rpc {self.rpc.stats.calls} calls · {self.rpc.stats.errors} errors · p50 {self.rpc.stats.p50_ms:.0f} ms")

    def table(self, limit: int = 20) -> list[dict]:
        rows = sorted(self.launches.values(), key=lambda l: l.block, reverse=True)[:limit]
        return [
            {
                "age_blk": l.age(self.head),
                "symbol": l.symbol,
                "curve": l.curve,
                "buys_60": l.buys_first_60,
                "buyers": len(l.buyers),
                "volume": f"{l.volume:,.0f} USDG" if l.quote == "USDG" else f"{l.volume:.3f} ETH",
                "crowd": len(l.crowd),
                "score": self.score(l),
                "verdict": l.verdict,
                "why": l.why,
            }
            for l in rows
        ]

    def snapshot(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({"head": self.head, "time": time.time(), "counters": self.counters, "launches": self.table(200)}, indent=1), encoding="utf-8")
