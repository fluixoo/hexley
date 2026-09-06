"""GENEALOGIST: who enters launches together.

Input: for each launch, the first N curve buyers with their block numbers.
Two wallets are linked on a launch when both are among the early buyers and
their entries are within `window_blocks` of each other. Wallets linked on at
least `min_shared` launches end up in the same cluster (union-find).

Bundlers (4337) and routers are excluded up front, otherwise every user of the
same bot lands in one giant cluster and the signal is gone.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from .. import constants as C
from .. import decode as D
from ..models import Cluster


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


class Genealogist:
    def __init__(self, window_blocks: int = 30, min_shared: int = 4, exclude: set[str] | None = None) -> None:
        self.window_blocks = window_blocks
        self.min_shared = min_shared
        self.exclude = {a.lower() for a in (exclude or set())} | {C.LAUNCHPAD_ROUTER}

    @staticmethod
    def is_bundler(addr: str) -> bool:
        return addr.lower().startswith(C.BUNDLER_PREFIX)

    def pairs(self, entries: dict[str, list[tuple[int, str]]]) -> Counter:
        """entries: token -> [(block, wallet), ...] early buyers in order.
        Returns Counter of (wallet_a, wallet_b) -> shared launches."""
        cnt: Counter = Counter()
        for _token, rows in entries.items():
            rows = [(b, w.lower()) for b, w in rows if w.lower() not in self.exclude and not self.is_bundler(w)]
            seen_pair: set[tuple[str, str]] = set()
            for (b1, w1), (b2, w2) in combinations(rows, 2):
                if w1 == w2 or abs(b1 - b2) > self.window_blocks:
                    continue
                key = (w1, w2) if w1 < w2 else (w2, w1)
                if key not in seen_pair:
                    seen_pair.add(key)
                    cnt[key] += 1
        return cnt

    def cluster(self, entries: dict[str, list[tuple[int, str]]], kinds: dict[str, str] | None = None) -> list[Cluster]:
        cnt = self.pairs(entries)
        uf = UnionFind()
        strong = {k: v for k, v in cnt.items() if v >= self.min_shared}
        for (a, b) in strong:
            uf.union(a, b)
        groups: dict[str, list[str]] = defaultdict(list)
        for w in {w for pair in strong for w in pair}:
            groups[uf.find(w)].append(w)
        out: list[Cluster] = []
        for i, members in enumerate(sorted(groups.values(), key=len, reverse=True), start=1):
            members = sorted(members)
            shared = max((v for (a, b), v in strong.items() if a in members and b in members), default=0)
            kind_count = Counter((kinds or {}).get(m, "unknown") for m in members)
            out.append(Cluster(id=i, members=members, shared_launches=shared, kinds=dict(kind_count)))
        return out

    @staticmethod
    def wallet_kind(code: str) -> str:
        """eoa | 7702 | contract, from eth_getCode output."""
        c = D.strip0x(code)
        if not c:
            return "eoa"
        if D.is_7702(code):
            return "7702"
        return "contract"

    @staticmethod
    def crowd_set(clusters: list[Cluster], anchor: str) -> set[str]:
        """Members of the cluster that contains the anchor wallet (the leader)."""
        anchor = anchor.lower()
        for c in clusters:
            if anchor in c.members:
                return set(c.members)
        return {anchor}
