"""chaindesk: a six-agent on-chain desk for Robinhood Chain.

The desk reads the launchpad straight from raw logs (no indexer, no news feed),
scores wallets from their own trades, and brute-forces exit rules on the
resulting price paths. Everything is paper-only.
"""

__version__ = "0.3.0"
__all__ = ["__version__"]
