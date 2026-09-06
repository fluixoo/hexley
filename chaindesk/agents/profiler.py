"""PROFILER: what happens to price after the wallet buys.

Every entry becomes a normalized path: price / entry_price sampled per minute
from the *copier's* entry (the first trade after the leader, not the leader's
own fill; the difference is the copier premium and it is not small).

The scorecard is a handful of numbers that survive small samples:
  p(x1.5) p(x2) p(x3) p(x5) p(x10)   share of entries whose max reached the level
  median max, median low 1h, median close 6h
  copier premium, hold time
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class Scorecard:
    entries: int
    p_x1_5: float
    p_x2: float
    p_x3: float
    p_x5: float
    p_x10: float
    median_max_x: float
    median_low_1h_x: float
    median_close_6h_x: float
    copier_premium: float
    median_hold_min: float

    def as_dict(self) -> dict:
        return asdict(self)


class Profiler:
    LEVELS = (1.5, 2.0, 3.0, 5.0, 10.0)

    @staticmethod
    def normalize(prices: np.ndarray, entry_idx: int = 0) -> np.ndarray:
        p = np.asarray(prices, dtype=float)
        base = p[entry_idx]
        if base <= 0:
            raise ValueError("entry price must be positive")
        return p[entry_idx:] / base

    @staticmethod
    def max_after(path: np.ndarray, minutes: int | None = None) -> float:
        seg = path if minutes is None else path[: minutes + 1]
        return float(seg.max()) if len(seg) else float("nan")

    @staticmethod
    def min_after(path: np.ndarray, minutes: int) -> float:
        seg = path[: minutes + 1]
        return float(seg.min()) if len(seg) else float("nan")

    @staticmethod
    def close_at(path: np.ndarray, minutes: int) -> float:
        return float(path[min(minutes, len(path) - 1)])

    def score(self, paths: list[np.ndarray], premiums: list[float] | None = None, holds_min: list[float] | None = None) -> Scorecard:
        if not paths:
            raise ValueError("no paths to score")
        maxes = np.array([self.max_after(p) for p in paths])
        lows = np.array([self.min_after(p, 60) for p in paths])
        closes = np.array([self.close_at(p, 360) for p in paths])
        hit = {lvl: float((maxes >= lvl).mean()) for lvl in self.LEVELS}
        return Scorecard(
            entries=len(paths),
            p_x1_5=round(hit[1.5], 3),
            p_x2=round(hit[2.0], 3),
            p_x3=round(hit[3.0], 3),
            p_x5=round(hit[5.0], 3),
            p_x10=round(hit[10.0], 3),
            median_max_x=round(float(np.median(maxes)), 2),
            median_low_1h_x=round(float(np.median(lows)), 2),
            median_close_6h_x=round(float(np.median(closes)), 2),
            copier_premium=round(float(np.median(premiums)), 3) if premiums else 1.0,
            median_hold_min=round(float(np.median(holds_min)), 1) if holds_min else float("nan"),
        )

    @staticmethod
    def bootstrap(values: np.ndarray, stat=np.mean, n: int = 2000, ci: float = 0.90, seed: int = 7) -> tuple[float, float]:
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, len(values), size=(n, len(values)))
        s = np.sort(stat(values[idx], axis=1))
        lo = s[int((1 - ci) / 2 * n)]
        hi = s[int((1 + ci) / 2 * n) - 1]
        return float(lo), float(hi)
