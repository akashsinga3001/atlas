# Atlas — Conventions

Project-specific conventions accumulate here via Convention Sweep.

## Strategy logic

- New quantitative logic embedded in a strategy (e.g. regime detection, signal scoring) should be extracted as a standalone, pure module-level function in the strategy's `strategy.py` — not inlined in `execute()`. This keeps it independently auditable and callable in isolation (e.g. from a REPL or a future test) even when no test suite covers it yet, which matters most for logic that sizes or gates real capital. First applied in `compute_vol_regime()` in `nifty_iron_condor/strategy.py`.

## Frontend data loading

- Every async data slice in a Pinia store must use the shared `ResourceState<T>` pattern (`frontend/src/types/resource.ts` + `frontend/src/stores/helpers/resource.ts` — `loadResource`/`isStale`), not a one-off `loading`/`data` pair. A failed refresh sets `status: 'error'` and records the message but **never clears existing `data`** — the UI keeps showing the last known-good state with a staleness badge (`StaleBadge.vue`) rather than collapsing into a false "no data" empty state. This is the direct architectural fix for the pre-rebuild frontend's core bug (intermittent refresh failures rendering as empty states); every new store added in later stages must reuse it, not reinvent per-screen loading state.

## Config migrations

- Changes to a live strategy's config (e.g. `nifty_iron_condor`'s `strategy_versions.config`) ship as an Alembic migration that reads the JSON blob via `strategies.code`, guards with an idempotency check on the new key(s), and writes a symmetric `downgrade()` that restores the exact prior shape — see `f7a3c1e9b4d2` and `a2c5f8e1d9b7` for the reference pattern. Don't edit seeded config via a one-off script or manual DB update.
