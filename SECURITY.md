# Security

This project never handles private keys, never signs, and never sends transactions. The only outbound traffic is JSON-RPC reads to the public endpoints listed in `chaindesk/constants.py`.

If you find a way for this code to do anything else, open an issue with the reproduction. If it involves the RPC endpoints themselves, report to their operators, not here.
