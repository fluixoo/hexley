"""REFEREE: which exit rule would have paid, on these paths, with this delay.

A rule is (take-profit level, fraction sold at TP, stop level, time stop,
trailing stop). Instead of simulating every rule minute by minute we
precompute, per path, the first minute each level is hit (up and down).
A rule then resolves in O(1) per path and the whole grid is a few numpy ops.

Delay is modelled as entering `delay_min` minutes later at the price then,
which is exactly what a slow copier gets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product

import numpy as np


@dataclass
class Rule:
    tp: float  # take-profit multiple, e.g. 4.0
    tp_frac: float  # fraction sold at tp, rest rides to time stop / trail
    stop: float | None  # stop multiple, e.g. 0.6, or None
    time_stop_min: int  # forced exit
    trail: float | None  # trailing stop as drawdown from running max, e.g. 0.4 (=40%)

    def label(self) -> str:
        parts = [f"{int(self.tp_frac*100)}%@x{self.tp:g}", f"{self.time_stop_min}m"]
        if self.stop:
            parts.append(f"stop {self.stop:g}")
        if self.trail:
            parts.append(f"trail {int(self.trail*100)}%")
        return " · ".join(parts)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RuleResult:
    rule: Rule
    ev_pct: float  # mean return per entry, percent
    win_rate: float
    profit_factor: float
    n: int

    def as_dict(self) -> dict:
        d = asdict(self)
        d["label"] = self.rule.label()
        return d


class Referee:
    def __init__(self, paths: list[np.ndarray], horizon_min: int = 360) -> None:
        self.horizon = horizon_min
        self.paths = [self._pad(np.asarray(p, dtype=float), horizon_min + 1) for p in paths]
        self.P = np.vstack(self.paths)  # n_paths x (horizon+1)

    @staticmethod
    def _pad(p: np.ndarray, n: int) -> np.ndarray:
        if len(p) >= n:
            return p[:n]
        return np.concatenate([p, np.full(n - len(p), p[-1])])

    # ---- primitives ----------------------------------------------------------
    @staticmethod
    def first_hit_up(P: np.ndarray, level: float) -> np.ndarray:
        hit = P >= level
        idx = hit.argmax(axis=1)
        idx[~hit.any(axis=1)] = P.shape[1]  # never
        return idx

    @staticmethod
    def first_hit_down(P: np.ndarray, level: float) -> np.ndarray:
        hit = P <= level
        idx = hit.argmax(axis=1)
        idx[~hit.any(axis=1)] = P.shape[1]
        return idx

    @staticmethod
    def first_trail_hit(P: np.ndarray, trail: float) -> np.ndarray:
        run_max = np.maximum.accumulate(P, axis=1)
        hit = P <= run_max * (1 - trail)
        idx = hit.argmax(axis=1)
        idx[~hit.any(axis=1)] = P.shape[1]
        return idx

    # ---- evaluation ----------------------------------------------------------
    def entry_shifted(self, delay_min: int) -> np.ndarray:
        """Paths re-based to the price `delay_min` minutes after the signal."""
        if delay_min <= 0:
            return self.P
        d = min(delay_min, self.P.shape[1] - 1)
        base = self.P[:, d : d + 1]
        return self.P[:, d:] / base

    def evaluate(self, rule: Rule, delay_min: int = 0) -> RuleResult:
        P = self.entry_shifted(delay_min)
        n, T = P.shape
        t_tp = self.first_hit_up(P, rule.tp)
        t_stop = self.first_hit_down(P, rule.stop) if rule.stop else np.full(n, T)
        t_trail = self.first_trail_hit(P, rule.trail) if rule.trail else np.full(n, T)
        t_time = np.full(n, min(rule.time_stop_min, T - 1))
        rows = np.arange(n)

        # leg 1: the tp_frac part. exits at tp, or at whichever of stop/trail/time comes first
        t_exit1 = np.minimum.reduce([t_tp, t_stop, t_trail, t_time])
        px1 = np.where(t_exit1 == t_tp, rule.tp, P[rows, np.clip(t_exit1, 0, T - 1)])
        # leg 2: the remainder rides until stop / trail / time (tp does not close it)
        t_exit2 = np.minimum.reduce([t_stop, t_trail, t_time])
        px2 = P[rows, np.clip(t_exit2, 0, T - 1)]
        # if stop fires before tp, both legs exit at the stop
        stopped_first = (t_stop < t_tp) | (t_trail < t_tp)
        px1 = np.where(stopped_first, px2, px1)
        ret = rule.tp_frac * px1 + (1 - rule.tp_frac) * px2 - 1.0

        wins = ret > 0
        gross_win = ret[wins].sum()
        gross_loss = -ret[~wins].sum()
        pf = float(gross_win / gross_loss) if gross_loss > 0 else float("inf")
        return RuleResult(rule, ev_pct=round(float(ret.mean()) * 100, 2), win_rate=round(float(wins.mean()), 3), profit_factor=round(pf, 2), n=n)

    def grid(
        self,
        tps=(1.5, 2, 3, 4, 5, 8, 10),
        fracs=(0.5, 1.0),
        stops=(None, 0.8, 0.6, 0.4),
        time_stops=(15, 30, 60, 180, 360),
        trails=(None, 0.15, 0.25, 0.4),
        delay_min: int = 0,
        top: int = 10,
        min_win_rate: float = 0.0,
    ) -> list[RuleResult]:
        out = [
            self.evaluate(Rule(tp, f, s, ts, tr), delay_min)
            for tp, f, s, ts, tr in product(tps, fracs, stops, time_stops, trails)
        ]
        out = [r for r in out if r.win_rate >= min_win_rate]
        out.sort(key=lambda r: r.ev_pct, reverse=True)
        return out[:top]

    def delay_cliff(self, rule: Rule, delays=(0, 1, 3, 5, 15, 60)) -> dict[int, float]:
        return {d: self.evaluate(rule, d).ev_pct for d in delays}

    def bootstrap_ev(self, rule: Rule, n: int = 1000, ci: float = 0.90, seed: int = 7) -> tuple[float, float]:
        rng = np.random.default_rng(seed)
        evs = []
        idx_all = np.arange(len(self.paths))
        for _ in range(n):
            idx = rng.choice(idx_all, size=len(idx_all), replace=True)
            sub = Referee([self.paths[i] for i in idx], self.horizon)
            evs.append(sub.evaluate(rule).ev_pct)
        s = np.sort(evs)
        return float(s[int((1 - ci) / 2 * n)]), float(s[int((1 + ci) / 2 * n) - 1])
