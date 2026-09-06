"""Pure functions that turn hex into numbers. No network, fully unit-tested."""

from __future__ import annotations

from . import constants as C

WORD = 64  # hex chars per 32-byte word


def strip0x(h: str) -> str:
    return h[2:] if h.startswith("0x") else h


def word(data: str, i: int) -> int:
    """i-th 32-byte word of ABI-encoded data as an unsigned int."""
    d = strip0x(data)
    seg = d[i * WORD : (i + 1) * WORD]
    if len(seg) < WORD:
        raise ValueError(f"data has no word {i}")
    return int(seg, 16)


def signed(x: int, bits: int = 256) -> int:
    """Two's-complement reinterpretation. Uniswap v4 packs int128 amounts into
    full 32-byte words sign-extended, so decode at 256 bits."""
    return x - (1 << bits) if x >= (1 << (bits - 1)) else x


def topic_to_address(topic: str) -> str:
    return "0x" + strip0x(topic)[-40:].lower()


def address_to_topic(addr: str) -> str:
    return "0x" + "0" * 24 + strip0x(addr).lower()


def decode_curve_trade(data: str) -> tuple[int, int, int]:
    """(quote_amount, token_amount, fee) for both BUY and SELL curve events."""
    return word(data, 0), word(data, 1), word(data, 2)


def decode_v4_swap(data: str) -> tuple[int, int, int, int]:
    """(amount0, amount1, sqrtPriceX96, liquidity). Negative amount = the user paid it."""
    return signed(word(data, 0)), signed(word(data, 1)), word(data, 2), word(data, 3)


def decode_string_return(ret: str) -> str:
    """ABI string return (offset, length, bytes). Some tokens return bytes32; handle both."""
    d = strip0x(ret)
    if len(d) == WORD:  # bytes32 symbol
        return bytes.fromhex(d).rstrip(b"\x00").decode("utf-8", "replace")
    if len(d) < 2 * WORD:
        return ""
    off = int(d[:WORD], 16) * 2
    ln = int(d[off : off + WORD], 16) * 2
    raw = bytes.fromhex(d[off + WORD : off + WORD + ln])
    return raw.decode("utf-8", "replace")


def clean_symbol(sym: str, max_len: int = 12) -> str:
    return "".join(ch for ch in sym if 32 <= ord(ch) < 127).strip()[:max_len] or "?"


def is_launch_mint(log: dict) -> bool:
    """A launchpad token birth: Transfer(0x0 -> curve) of exactly LAUNCH_SUPPLY.
    ERC-721 mints share the topic but carry no data word, so the length check matters."""
    t = log.get("topics", [])
    if len(t) < 3 or t[0] != C.TOPIC_TRANSFER or t[1] != C.ZERO_TOPIC:
        return False
    data = log.get("data", "0x")
    if len(strip0x(data)) != WORD:
        return False
    return word(data, 0) == C.LAUNCH_SUPPLY


def quote_to_float(raw: int, quote: str) -> float:
    dec = 6 if quote == "USDG" else 18
    return raw / 10**dec


def sane_buy(amount: float, quote: str) -> bool:
    return amount <= C.MAX_SANE_BUY.get(quote, float("inf"))


def guess_quote(raw_quote_amount: int) -> str:
    """When no USDG/WETH transfer sits in the same tx, size tells the story:
    a 6-decimal USDG buy is < 1e12 raw, an 18-decimal ETH buy is not."""
    return "USDG" if raw_quote_amount < 10**12 else "ETH"


def slot0_to_price(sqrt_price_x96: int, dec0: int = 18, dec1: int = 6) -> float:
    """Uniswap v3 slot0 sqrtPriceX96 -> token1 per token0 (USDG per ETH for the reference pool)."""
    p = (sqrt_price_x96 / 2**96) ** 2
    return p * 10 ** (dec0 - dec1)


def is_7702(code: str) -> bool:
    return strip0x(code).lower().startswith("ef0100")


def delegate_of(code: str) -> str | None:
    c = strip0x(code).lower()
    return "0x" + c[6:46] if is_7702(code) and len(c) >= 46 else None
