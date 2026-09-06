"""Chain constants for Robinhood Chain (Arbitrum Orbit, chain id 4663).

Every value here was read off the chain itself or off a verified contract,
not copied from a blog post. If one of them drifts, `chaindesk doctor`
will tell you which one.
"""

CHAIN_ID = 4663
CHAIN_NAME = "robinhood"
BLOCK_TIME_S = 0.1  # measured 95..105 ms across a 10k-block sample

RPC_PRIMARY = "https://rpc.mainnet.chain.robinhood.com"
RPC_FALLBACK = "https://robinhood-rpc.publicnode.com"

# eth_getLogs hard limit on the public RPC: more than this many matches -> error.
MAX_LOG_RESULTS = 10_000

# ---- event topics -----------------------------------------------------------
TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# launchpad bonding curve events. data layout for both:
#   word0 quote amount, word1 token amount, word2 fee, word3 reserved (0)
TOPIC_CURVE_BUY = "0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455"
TOPIC_CURVE_SELL = "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df"
# Uniswap v4 PoolManager Swap(id, sender, amount0, amount1, sqrtPriceX96, liquidity, tick, fee)
TOPIC_V4_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
ZERO_TOPIC = "0x" + "00" * 32

# ---- addresses (lowercase) --------------------------------------------------
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"  # 6 decimals
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"  # 18 decimals
ETH_USDG_POOL_V3 = "0x52e65b17fb6e5ba00ed806f37afcd2daa50271ca"  # slot0 -> ETH price
LAUNCHPAD_ROUTER = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"
V4_POOL_MANAGER = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
DELEGATE_7702 = "0xe6cae83bde06e4c305530e199d7217f42808555b"  # EIP-7702 delegate seen on user wallets

# a fresh launchpad token mints exactly 1e9 * 1e18 to its own bonding curve
LAUNCH_SUPPLY = 10**27

QUOTE_DECIMALS = {USDG: 6, WETH: 18, "ETH": 18}

# implausible single-buy sizes. above these the quote token was mis-detected.
MAX_SANE_BUY = {"USDG": 2_000_000.0, "ETH": 200.0}

# 4337 bundlers on this chain share a vanity prefix. good enough as a first filter,
# the genealogist confirms with eth_getCode.
BUNDLER_PREFIX = "0x4337"

# ---- function selectors -----------------------------------------------------
SEL_SYMBOL = "0x95d89b41"
SEL_DECIMALS = "0x313ce567"
SEL_SLOT0 = "0x3850c7bd"
SEL_BALANCE_OF = "0x70a08231"
