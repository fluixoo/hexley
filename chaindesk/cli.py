"""chaindesk command line.

    chaindesk doctor                      check RPC, chain id, block time, ETH price
    chaindesk watch [--blocks N]          live launch radar (backfill + stream)
    chaindesk launches --last 2000        list launches in the last N blocks
    chaindesk wallet 0x... --blocks 60000 transfers of a wallet, per token
    chaindesk price                       ETH/USDG from the v3 pool slot0
    chaindesk referee paths.json          brute-force exit rules on saved price paths
    chaindesk cluster entries.json        co-entry clusters from early-buyer lists
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from . import __version__
from . import constants as C
from . import decode as D
from .agents import Clerk, Genealogist, Profiler, Referee, Tap
from .desk import Desk, DeskConfig
from .rpc import Rpc


def _rpc(args) -> Rpc:
    return Rpc(url=args.rpc) if getattr(args, "rpc", None) else Rpc()


def cmd_doctor(args) -> int:
    rpc = _rpc(args)
    cid = int(rpc.call("eth_chainId"), 16)
    head = rpc.block_number()
    tap = Tap(rpc)
    bt = tap.block_time_ms(1000)
    px = tap.eth_price_usdg()
    ok = cid == C.CHAIN_ID
    print(f"rpc        {rpc.url}")
    print(f"chain id   {cid} {'ok' if ok else 'MISMATCH, expected ' + str(C.CHAIN_ID)}")
    print(f"head       {head:,}")
    print(f"block time {bt:.0f} ms (last 1000 blocks)")
    print(f"eth/usdg   {px:,.2f} (pool {C.ETH_USDG_POOL_V3[:10]}… slot0)")
    print(f"latency    p50 {rpc.stats.p50_ms:.0f} ms over {rpc.stats.calls} calls")
    return 0 if ok else 1


def cmd_price(args) -> int:
    print(f"{Tap(_rpc(args)).eth_price_usdg():.2f}")
    return 0


def cmd_watch(args) -> int:
    cfg = DeskConfig.from_toml(args.config) if args.config else DeskConfig()
    if args.leader:
        cfg.leader = args.leader
    cfg.backfill_blocks = args.backfill
    desk = Desk(cfg, _rpc(args))
    try:
        desk.run(blocks=args.blocks)
    except KeyboardInterrupt:
        pass
    rows = desk.table(args.top)
    if rows:
        print()
        print(f"{'age':>6} {'token':<10} {'buys60':>6} {'buyers':>6} {'volume':>14} {'crowd':>5} {'score':>5} {'verdict':<7} why")
        for r in rows:
            print(f"{r['age_blk']:>6} {r['symbol']:<10} {r['buys_60']:>6} {r['buyers']:>6} {r['volume']:>14} {r['crowd']:>5} {r['score']:>5} {r['verdict']:<7} {r['why']}")
    if args.snapshot:
        desk.snapshot(args.snapshot)
        print(f"snapshot -> {args.snapshot}")
    return 0


def cmd_launches(args) -> int:
    rpc = _rpc(args)
    tap = Tap(rpc)
    head = rpc.block_number()
    a = head - args.last
    found = []
    for s in range(a, head + 1, 150):
        rr = tap.scan_range(s, min(s + 149, head))
        found.extend(rr.launches)
    print(f"{len(found)} launches in blocks {a:,}..{head:,} ({args.last * C.BLOCK_TIME_S / 60:.1f} min)")
    for l in found:
        print(f"{l.block:>12,}  ${l.symbol:<10} token {l.token}  curve {l.curve}")
    return 0


def cmd_wallet(args) -> int:
    rpc = _rpc(args)
    tap = Tap(rpc)
    head = rpc.block_number()
    logs = tap.wallet_transfers(args.address, head - args.blocks, head)
    me = D.address_to_topic(args.address)
    by_token: Counter = Counter()
    first_seen: dict[str, int] = {}
    for lg in logs:
        tok = lg["address"].lower()
        by_token[tok] += 1
        first_seen.setdefault(tok, int(lg["blockNumber"], 16))
    print(f"{len(logs)} transfers · {len(by_token)} tokens · last {args.blocks:,} blocks")
    for tok, n in by_token.most_common(args.top):
        sym = tap.symbol(tok)
        direction = "in " if any(lg["address"].lower() == tok and lg["topics"][2] == me for lg in logs) else "out"
        print(f"{first_seen[tok]:>12,}  ${sym:<10} {tok}  {n:>3} transfers  first {direction}")
    return 0


def cmd_referee(args) -> int:
    data = json.loads(Path(args.paths).read_text(encoding="utf-8"))
    paths = [np.asarray(p, dtype=float) for p in data["paths"]]
    ref = Referee(paths, horizon_min=args.horizon)
    top = ref.grid(top=args.top, delay_min=args.delay, min_win_rate=args.min_win)
    print(f"{len(paths)} paths · grid evaluated · delay {args.delay} min")
    print(f"{'#':>2} {'rule':<34} {'EV':>8} {'win':>5} {'PF':>6}")
    for i, r in enumerate(top, 1):
        print(f"{i:>2} {r.rule.label():<34} {r.ev_pct:>+7.1f}% {r.win_rate:>5.0%} {r.profit_factor:>6.2f}")
    if top:
        cliff = ref.delay_cliff(top[0].rule)
        print("delay cliff (rule 1): " + " · ".join(f"{d}m {ev:+.1f}%" for d, ev in cliff.items()))
        if args.ci:
            lo, hi = ref.bootstrap_ev(top[0].rule, n=args.ci)
            print(f"bootstrap 90% CI (rule 1): {lo:+.1f}% .. {hi:+.1f}%")
    return 0


def cmd_profile(args) -> int:
    data = json.loads(Path(args.paths).read_text(encoding="utf-8"))
    paths = [np.asarray(p, dtype=float) for p in data["paths"]]
    card = Profiler().score(paths, data.get("premiums"), data.get("holds_min"))
    for k, v in card.as_dict().items():
        print(f"{k:<18} {v}")
    return 0


def cmd_cluster(args) -> int:
    data = json.loads(Path(args.entries).read_text(encoding="utf-8"))
    entries = {tok: [(int(b), w) for b, w in rows] for tok, rows in data["entries"].items()}
    g = Genealogist(window_blocks=args.window, min_shared=args.min_shared)
    clusters = g.cluster(entries, data.get("kinds"))
    print(f"{len(entries)} launches · {len(clusters)} clusters (window {args.window} blk, min shared {args.min_shared})")
    for c in clusters[: args.top]:
        kinds = " ".join(f"{k} {v}" for k, v in c.kinds.items())
        print(f"#{c.id:<3} {len(c.members):>3} wallets · {c.shared_launches:>2} shared · {kinds}")
        for m in c.members[:8]:
            print(f"      {m}")
    return 0


def cmd_report(args) -> int:
    data = json.loads(Path(args.paths).read_text(encoding="utf-8"))
    paths = [np.asarray(p, dtype=float) for p in data["paths"]]
    card = Profiler().score(paths, data.get("premiums"), data.get("holds_min"))
    ref = Referee(paths)
    top = ref.grid(top=5)
    cliff = ref.delay_cliff(top[0].rule)
    ci = ref.bootstrap_ev(top[0].rule, n=300)
    clerk = Clerk(args.out)
    verdict = clerk.verdict(top[0], cliff, args.lag_blocks)
    md = clerk.report(data.get("wallet", "?"), tuple(data.get("window", ("?", "?"))), card, top, cliff, verdict, ci)
    p = clerk.save(args.name, md, {"scorecard": card.as_dict(), "rules": [r.as_dict() for r in top], "cliff": cliff, "verdict": verdict})
    print(md)
    print(f"\n-> {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="chaindesk", description="six-agent on-chain desk for Robinhood Chain (paper only)")
    p.add_argument("--version", action="version", version=f"chaindesk {__version__}")
    p.add_argument("--rpc", help="override RPC url")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check rpc, chain id, block time, eth price").set_defaults(fn=cmd_doctor)
    sub.add_parser("price", help="ETH/USDG from pool slot0").set_defaults(fn=cmd_price)

    w = sub.add_parser("watch", help="live launch radar")
    w.add_argument("--blocks", type=int, default=None, help="stop after N live blocks (default: run until Ctrl-C)")
    w.add_argument("--backfill", type=int, default=900)
    w.add_argument("--leader", help="wallet to flag on every transfer")
    w.add_argument("--config", help="desk.toml with leader + crowd set")
    w.add_argument("--top", type=int, default=20)
    w.add_argument("--snapshot", help="write launches table to this json")
    w.set_defaults(fn=cmd_watch)

    l = sub.add_parser("launches", help="launches in the last N blocks")
    l.add_argument("--last", type=int, default=2000)
    l.set_defaults(fn=cmd_launches)

    wa = sub.add_parser("wallet", help="ERC-20 transfers of a wallet")
    wa.add_argument("address")
    wa.add_argument("--blocks", type=int, default=60_000)
    wa.add_argument("--top", type=int, default=30)
    wa.set_defaults(fn=cmd_wallet)

    r = sub.add_parser("referee", help="brute-force exit rules on saved paths")
    r.add_argument("paths", help='json: {"paths": [[1.0, 1.1, ...], ...]}')
    r.add_argument("--horizon", type=int, default=360)
    r.add_argument("--delay", type=int, default=0)
    r.add_argument("--top", type=int, default=10)
    r.add_argument("--min-win", type=float, default=0.0)
    r.add_argument("--ci", type=int, default=0, help="bootstrap resamples for rule 1 (0 = off)")
    r.set_defaults(fn=cmd_referee)

    pr = sub.add_parser("profile", help="scorecard from saved paths")
    pr.add_argument("paths")
    pr.set_defaults(fn=cmd_profile)

    c = sub.add_parser("cluster", help="co-entry clusters")
    c.add_argument("entries", help='json: {"entries": {token: [[block, wallet], ...]}, "kinds": {wallet: kind}}')
    c.add_argument("--window", type=int, default=30)
    c.add_argument("--min-shared", type=int, default=4)
    c.add_argument("--top", type=int, default=10)
    c.set_defaults(fn=cmd_cluster)

    rp = sub.add_parser("report", help="scorecard + rules + verdict as markdown")
    rp.add_argument("paths")
    rp.add_argument("--name", default="leader")
    rp.add_argument("--out", default="reports")
    rp.add_argument("--lag-blocks", type=int, default=None, help="measured copy lag on your route, in blocks")
    rp.set_defaults(fn=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
