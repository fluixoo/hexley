"""Thin JSON-RPC client with the quirks of the Robinhood Chain public nodes baked in.

Quirks we handle:
* the primary node caps eth_getLogs at 10,000 matches per call and answers with
  "logs matched by query exceeds limit". We halve the range and retry.
* some historical ranges answer "Archive requests are not supported". Same fix.
* the publicnode fallback rejects topic-only getLogs (no address filter), so
  getLogs never falls back, everything else does.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from . import constants as C


class RpcError(RuntimeError):
    pass


@dataclass
class RpcStats:
    calls: int = 0
    errors: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def p50_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return s[len(s) // 2]


class Rpc:
    def __init__(
        self,
        url: str = C.RPC_PRIMARY,
        fallback: str | None = C.RPC_FALLBACK,
        timeout: float = 20.0,
        retries: int = 2,
    ) -> None:
        self.url = url
        self.fallback = fallback
        self.timeout = timeout
        self.retries = retries
        self.stats = RpcStats()
        self._id = 0

    # ---- low level ----------------------------------------------------------
    def _post(self, url: str, method: str, params: list) -> Any:
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": f"chaindesk/{__import__('chaindesk').__version__}"})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                payload = json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            self.stats.errors += 1
            raise RpcError(f"{method}: transport error: {e}") from e
        finally:
            self.stats.calls += 1
            self.stats.latencies_ms.append((time.perf_counter() - t0) * 1000)
        if "error" in payload:
            self.stats.errors += 1
            raise RpcError(f"{method}: {payload['error'].get('message', payload['error'])}")
        return payload["result"]

    def call(self, method: str, params: list | None = None) -> Any:
        params = params or []
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return self._post(self.url, method, params)
            except RpcError as e:
                last = e
                msg = str(e)
                if method == "eth_getLogs" and ("limit" in msg or "Archive" in msg):
                    raise  # caller splits the range, retrying the same range is pointless
                time.sleep(0.25 * (attempt + 1))
        if self.fallback and method != "eth_getLogs":
            try:
                return self._post(self.fallback, method, params)
            except RpcError as e:
                last = e
        raise RpcError(str(last))

    # ---- helpers ------------------------------------------------------------
    def block_number(self) -> int:
        return int(self.call("eth_blockNumber"), 16)

    def get_block(self, n: int, full_tx: bool = False) -> dict:
        return self.call("eth_getBlockByNumber", [hex(n), full_tx])

    def get_tx(self, tx_hash: str) -> dict:
        return self.call("eth_getTransactionByHash", [tx_hash])

    def get_receipt(self, tx_hash: str) -> dict:
        return self.call("eth_getTransactionReceipt", [tx_hash])

    def get_code(self, addr: str) -> str:
        return self.call("eth_getCode", [addr, "latest"])

    def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        return self.call("eth_call", [{"to": to, "data": data}, block])

    def get_balance(self, addr: str) -> int:
        return int(self.call("eth_getBalance", [addr, "latest"]), 16)

    def get_nonce(self, addr: str) -> int:
        return int(self.call("eth_getTransactionCount", [addr, "latest"]), 16)

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        topics: list[str | None | list[str]] | None = None,
        address: str | list[str] | None = None,
        min_chunk: int = 32,
    ) -> list[dict]:
        """eth_getLogs over an arbitrary range, splitting on the node's limits."""
        out: list[dict] = []
        stack: list[tuple[int, int]] = [(from_block, to_block)]
        while stack:
            a, b = stack.pop()
            flt: dict[str, Any] = {"fromBlock": hex(a), "toBlock": hex(b)}
            if topics is not None:
                flt["topics"] = topics
            if address is not None:
                flt["address"] = address
            try:
                out.extend(self.call("eth_getLogs", [flt]))
            except RpcError as e:
                if b - a + 1 <= min_chunk:
                    raise RpcError(f"getLogs {a}..{b} failed even at min chunk: {e}") from e
                mid = a + (b - a) // 2
                stack.append((mid + 1, b))
                stack.append((a, mid))
        out.sort(key=lambda lg: (int(lg["blockNumber"], 16), int(lg["logIndex"], 16)))
        return out

    def iter_logs(
        self,
        from_block: int,
        to_block: int,
        chunk: int = 100_000,
        **kw: Any,
    ) -> Iterable[dict]:
        for a in range(from_block, to_block + 1, chunk):
            b = min(a + chunk - 1, to_block)
            yield from self.get_logs(a, b, **kw)
