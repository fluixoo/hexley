"""Desk ingest on synthetic RangeResults. No network."""

from chaindesk import constants as C
from chaindesk import decode as D
from chaindesk.agents.tap import RangeResult
from chaindesk.desk import Desk, DeskConfig
from chaindesk.models import Launch
from chaindesk.rpc import Rpc


def w(x: int) -> str:
    return f"{x:064x}"


CURVE = "0x" + "c1" * 20
BUYER = ["0x" + f"{i:040x}" for i in range(1, 20)]
CROWD = "0x" + "cc" * 20


def buy_log(block: int, quote_raw: int, tx: str):
    return {"address": CURVE, "topics": [C.TOPIC_CURVE_BUY], "data": "0x" + w(quote_raw) + w(10**21) + w(quote_raw // 100) + w(0), "blockNumber": hex(block), "transactionHash": tx, "logIndex": "0x1"}


def transfer_log(block: int, frm: str, to: str, token: str = CURVE, tx: str = "0xt"):
    return {"address": token, "topics": [C.TOPIC_TRANSFER, D.address_to_topic(frm), D.address_to_topic(to)], "data": "0x" + w(10**21), "blockNumber": hex(block), "transactionHash": tx, "logIndex": "0x2"}


def make_desk(crowd=()):
    return Desk(DeskConfig(crowd=set(crowd)), rpc=Rpc(url="http://127.0.0.1:9", fallback=None, retries=0))


def test_launch_then_fire_on_volume():
    desk = make_desk()
    launch = Launch(token="0x" + "aa" * 20, curve=CURVE, block=100, tx="0x0", symbol="TEST")
    desk.ingest(RangeResult(100, 100, [launch], [], []), live=False)
    buys = [buy_log(101 + i, 5 * 10**16, f"0x{i:x}") for i in range(12)]  # 0.05 ETH each
    trs = [transfer_log(101 + i, CURVE, BUYER[i % 8], tx=f"0x{i:x}") for i in range(12)]
    desk.ingest(RangeResult(101, 112, [], buys, trs), live=False)
    l = desk.launches[CURVE]
    assert l.buys_first_60 == 12 and len(l.buyers) == 8
    assert l.verdict == "fire"
    assert abs(l.volume - 12 * 0.05) < 1e-9
    assert desk.counters["buys"] == 12


def test_crowd_wallet_fires_immediately():
    desk = make_desk(crowd=[CROWD])
    launch = Launch(token="0x" + "aa" * 20, curve=CURVE, block=100, tx="0x0", symbol="TEST")
    desk.ingest(RangeResult(100, 100, [launch], [], []), live=False)
    desk.ingest(RangeResult(101, 101, [], [buy_log(101, 10**6, "0x1")], [transfer_log(101, CURVE, CROWD, tx="0x1")]), live=False)
    l = desk.launches[CURVE]
    assert l.verdict == "fire" and CROWD in l.crowd
    assert desk.counters["crowd_hits"] == 1


def test_quiet_launch_closes_after_300_blocks():
    desk = make_desk()
    launch = Launch(token="0x" + "aa" * 20, curve=CURVE, block=100, tx="0x0", symbol="TEST")
    desk.ingest(RangeResult(100, 100, [launch], [], []), live=False)
    desk.ingest(RangeResult(101, 120, [], [buy_log(105, 10**6, "0x1")], []), live=False)
    assert desk.launches[CURVE].verdict == "pass"
    desk.ingest(RangeResult(401, 420, [], [], []), live=False)
    assert desk.launches[CURVE].verdict == "closed"


def test_implausible_quote_is_rejected_not_counted():
    desk = make_desk()
    launch = Launch(token="0x" + "aa" * 20, curve=CURVE, block=100, tx="0x0", symbol="TEST")
    desk.ingest(RangeResult(100, 100, [launch], [], []), live=False)
    desk.ingest(RangeResult(101, 101, [], [buy_log(101, 8 * 10**27, "0x1")], []), live=False)
    assert desk.launches[CURVE].volume == 0.0
    assert desk.decoder.rejected == 1
