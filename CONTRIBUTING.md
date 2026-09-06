# Contributing

## Setup

```bash
git clone https://github.com/fluixoo/hexley
cd hexley
pip install -e ".[dev]"
make test && make lint
```

Tests are offline. If you add a test that needs the RPC, mark it `@pytest.mark.live` and skip by default.

## Rules

- Every number in `docs/` carries a date and a source file in `data/`. Results files are never edited after the fact; add a new dated file.
- Every on-chain constant in `constants.py` gets a comment saying how it was verified.
- No em dashes in prose. No emoji in code.
- A bug report with a block number and a tx hash goes to the front of the queue.
- Nothing that sends a transaction will be merged. This is a reading desk.

## Layout for a new seat

1. `chaindesk/agents/<name>.py` with a class whose public methods are pure where possible
2. `tests/test_<name>.py` with fixtures, no network
3. `docs/agents/README.md` row + section
4. wire it in `desk.py` only if it runs live
