"""CLERK: writes it down. Markdown report, JSON snapshot, and the verdict line.

The verdict is deliberately boring: it only says whether the measured copy lag
is inside the delay cliff of the best rule. No lag measurement, no size.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .profiler import Scorecard
from .referee import RuleResult


class Clerk:
    def __init__(self, out_dir: str | Path = "reports") -> None:
        self.out_dir = Path(out_dir)
        self.lines: list[str] = []

    def log(self, who: str, msg: str) -> None:
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        self.lines.append(f"{ts} {who:<12} {msg}")
        print(self.lines[-1])

    @staticmethod
    def verdict(best: RuleResult, delay_cliff: dict[int, float], measured_lag_blocks: int | None, block_time_s: float = 0.1) -> str:
        if measured_lag_blocks is None:
            return "no size until copy lag is measured on this route"
        lag_s = measured_lag_blocks * block_time_s
        # the cliff is keyed in minutes; anything under one minute maps to the 1-minute EV
        key = min((k for k in delay_cliff if k * 60 >= lag_s), default=max(delay_cliff))
        ev_at_lag = delay_cliff[key]
        if ev_at_lag <= 0:
            return f"do not copy: EV at measured lag ({lag_s:.1f}s) is {ev_at_lag:+.1f}%"
        if ev_at_lag < best.ev_pct * 0.5:
            return f"fix routing before sizing up: EV {ev_at_lag:+.1f}% at {lag_s:.1f}s vs {best.ev_pct:+.1f}% at zero lag"
        return f"route is inside the cliff: EV {ev_at_lag:+.1f}% at {lag_s:.1f}s lag · paper size only"

    def report(
        self,
        wallet: str,
        window: tuple[str, str],
        card: Scorecard,
        rules: list[RuleResult],
        cliff: dict[int, float],
        verdict: str,
        ci: tuple[float, float] | None = None,
    ) -> str:
        md = [
            f"# Leader scorecard · `{wallet}`",
            "",
            f"window {window[0]} → {window[1]} UTC · {card.entries} entries scored · computed {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
            "",
            "## Price after the copier's entry",
            "",
            "| metric | value |",
            "|---|---|",
            f"| p(x1.5) · p(x2) · p(x3) · p(x5) · p(x10) | {card.p_x1_5:.2f} · {card.p_x2:.2f} · {card.p_x3:.2f} · {card.p_x5:.2f} · {card.p_x10:.2f} |",
            f"| median max | {card.median_max_x:.2f}x |",
            f"| median low, first hour | {card.median_low_1h_x:.2f}x |",
            f"| median close, 6 h | {card.median_close_6h_x:.2f}x |",
            f"| copier premium (copier entry / leader fill) | {card.copier_premium:.3f} |",
            f"| leader median hold | {card.median_hold_min:.1f} min |",
            "",
            "## Exit rules, best by EV",
            "",
            "| # | rule | EV | win | PF |",
            "|---|---|---|---|---|",
        ]
        for i, r in enumerate(rules, 1):
            md.append(f"| {i} | {r.rule.label()} | {r.ev_pct:+.1f}% | {r.win_rate:.0%} | {r.profit_factor:.2f} |")
        if ci:
            md += ["", f"bootstrap 90% CI for rule 1: {ci[0]:+.1f}% .. {ci[1]:+.1f}%"]
        md += ["", "## Delay cliff (rule 1, EV by entry delay)", "", "| delay | EV |", "|---|---|"]
        for d, ev in cliff.items():
            md.append(f"| {d} min | {ev:+.1f}% |")
        md += ["", "## Verdict", "", f"**{verdict}**", "", "_paper only. nothing here is an order, a signal, or advice._"]
        return "\n".join(md)

    def save(self, name: str, markdown: str, snapshot: dict | None = None) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        p = self.out_dir / f"{name}.md"
        p.write_text(markdown, encoding="utf-8")
        if snapshot is not None:
            (self.out_dir / f"{name}.json").write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
        return p
