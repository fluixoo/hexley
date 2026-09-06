from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Launch:
    token: str
    curve: str
    block: int
    tx: str
    symbol: str = "?"
    quote: str = "ETH"
    buys: int = 0
    buys_first_60: int = 0
    volume: float = 0.0
    buyers: set[str] = field(default_factory=set)
    crowd: set[str] = field(default_factory=set)
    verdict: str = "pass"
    why: str = ""

    def age(self, head: int) -> int:
        return head - self.block


@dataclass
class Receipt:
    tx: str
    block: int
    kind: str  # curve_buy | curve_sell | v4_swap | transfer
    token: str
    quote: str
    quote_amount: float
    token_amount: float
    fee: float = 0.0
    paid: bool = True  # sign test: True when the user paid the quote


@dataclass
class Cluster:
    id: int
    members: list[str]
    shared_launches: int
    kinds: dict[str, int]
