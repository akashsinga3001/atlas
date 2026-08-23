# Atlas — Conventions

Project-specific conventions accumulate here via Convention Sweep.

## Strategy logic

- New quantitative logic embedded in a strategy (e.g. regime detection, signal scoring) should be extracted as a standalone, pure module-level function in the strategy's `strategy.py` — not inlined in `execute()`. This keeps it independently auditable and callable in isolation (e.g. from a REPL or a future test) even when no test suite covers it yet, which matters most for logic that sizes or gates real capital. First applied in `compute_vol_regime()` in `nifty_iron_condor/strategy.py`.

## Config migrations

- Changes to a live strategy's config (e.g. `nifty_iron_condor`'s `strategy_versions.config`) ship as an Alembic migration that reads the JSON blob via `strategies.code`, guards with an idempotency check on the new key(s), and writes a symmetric `downgrade()` that restores the exact prior shape — see `f7a3c1e9b4d2` and `a2c5f8e1d9b7` for the reference pattern. Don't edit seeded config via a one-off script or manual DB update.
