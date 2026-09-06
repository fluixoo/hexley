from chaindesk import constants as C
from chaindesk import decode as D


def w(x: int) -> str:
    return f"{x:064x}"


def test_signed_sign_extension():
    assert D.signed(5) == 5
    assert D.signed(2**256 - 1) == -1
    assert D.signed(2**255) == -(2**255)
    assert D.signed(2**128 - 1, bits=128) == -1


def test_topic_address_roundtrip():
    a = "0x5fa57fcaf86e137cb8185c4cb2c01ea7b5b14cfb"
    assert D.topic_to_address(D.address_to_topic(a)) == a
    assert len(D.address_to_topic(a)) == 66


def test_curve_trade_decode():
    data = "0x" + w(1_500_000) + w(12_345 * 10**18) + w(15_000) + w(0)
    q, t, f = D.decode_curve_trade(data)
    assert (q, t, f) == (1_500_000, 12_345 * 10**18, 15_000)
    assert D.guess_quote(q) == "USDG"
    assert D.quote_to_float(q, "USDG") == 1.5


def test_v4_swap_negative_means_paid():
    amount0 = (2**256) - 3 * 10**17  # -0.3 ETH
    amount1 = 9 * 10**21
    data = "0x" + w(amount0) + w(amount1) + w(2**96) + w(10**18)
    a0, a1, sqrtp, liq = D.decode_v4_swap(data)
    assert a0 == -3 * 10**17
    assert a1 == 9 * 10**21
    assert sqrtp == 2**96


def test_string_return_dynamic_and_bytes32():
    sym = b"HEXLEY"
    dyn = "0x" + w(32) + w(len(sym)) + sym.hex().ljust(64, "0")
    assert D.decode_string_return(dyn) == "HEXLEY"
    b32 = "0x" + sym.hex().ljust(64, "0")
    assert D.decode_string_return(b32) == "HEXLEY"
    assert D.clean_symbol("\x00\x01DOGE\n") == "DOGE"


def test_launch_mint_filter():
    good = {"topics": [C.TOPIC_TRANSFER, C.ZERO_TOPIC, D.address_to_topic("0x" + "ab" * 20)], "data": "0x" + w(C.LAUNCH_SUPPLY)}
    nft = {"topics": [C.TOPIC_TRANSFER, C.ZERO_TOPIC, D.address_to_topic("0x" + "ab" * 20), w(7)], "data": "0x"}
    wrong_amount = {**good, "data": "0x" + w(C.LAUNCH_SUPPLY - 1)}
    assert D.is_launch_mint(good)
    assert not D.is_launch_mint(nft)
    assert not D.is_launch_mint(wrong_amount)


def test_slot0_price_is_in_a_sane_range():
    # sqrtPriceX96 observed on the ETH/USDG v3 pool while ETH traded near $2,500
    sqrt_p = int(3.96e24)
    px = D.slot0_to_price(sqrt_p)
    assert 2_000 < px < 3_000


def test_7702_delegate():
    code = "0xef0100" + "e6cae83bde06e4c305530e199d7217f42808555b"
    assert D.is_7702(code)
    assert D.delegate_of(code) == C.DELEGATE_7702
    assert not D.is_7702("0x")
    assert D.delegate_of("0x6080604052") is None


def test_sane_buy_guard():
    assert D.sane_buy(0.5, "ETH")
    assert not D.sane_buy(8_189_364_259.0, "ETH")
    assert not D.sane_buy(3_000_000.0, "USDG")
