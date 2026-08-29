# Atlas — Conventions

Project-specific conventions accumulate here via Convention Sweep.

## Strategy logic

- New quantitative logic embedded in a strategy (e.g. regime detection, signal scoring) should be extracted as a standalone, pure module-level function in the strategy's `strategy.py` — not inlined in `execute()`. This keeps it independently auditable and callable in isolation (e.g. from a REPL or a future test) even when no test suite covers it yet, which matters most for logic that sizes or gates real capital. First applied in `compute_vol_regime()` in `nifty_iron_condor/strategy.py`.

## Frontend data loading

- Every async data slice in a Pinia store must use the shared `ResourceState<T>` pattern (`frontend/src/types/resource.ts` + `frontend/src/stores/helpers/resource.ts` — `loadResource`/`isStale`), not a one-off `loading`/`data` pair. A failed refresh sets `status: 'error'` and records the message but **never clears existing `data`** — the UI keeps showing the last known-good state with a staleness badge (`StaleBadge.vue`) rather than collapsing into a false "no data" empty state. This is the direct architectural fix for the pre-rebuild frontend's core bug (intermittent refresh failures rendering as empty states); every new store added in later stages must reuse it, not reinvent per-screen loading state.

## Migrations vs. data updates

- Alembic migrations are for DB/table structure changes only (`op.create_table`, `op.add_column`, `op.alter_column`, etc.) — never for seeding or updating row data, including strategy `config` JSON blobs, schedule entries, or one-off corrections. Data updates (e.g. changing a live strategy's `strategy_versions.config`, like `account_capital_pct`) go directly via `psql`/the Postgres UI, not a migration. Established 2026-08-29 after removing 7 pre-existing pure-DML migrations from the history for exactly this reason (they carried no schema change, only `conn.execute(sa.text(...))` data statements) — see git history for `backend/alembic/versions/` around that date if the old pattern needs to be understood.

## Strategy config schemas

- When a strategy's live config has nested keys the generic config UI can't render (it only supports flat scalar/enum/array top-level fields), its Pydantic schema should declare only the fields meant to be UI-editable and use `model_config = ConfigDict(extra="allow")` for the rest — never model the full nested shape just to be "complete." First applied in `MomentumScreenerConfig` (`backend/app/schemas/strategy_config.py`).

## Risk checks

- A risk-limit check that's purely a function of current config (e.g. capital-allocation overallocation) should be computed live from existing services, not persisted like the kill switch or a circuit breaker — no separate "acknowledge" step needed, since it self-clears the moment config is corrected. Reserve the persisted kill-switch/circuit-breaker pattern for checks driven by trading history or realized loss events. First applied in the `OVERALLOCATED` guard in `TradeService.run_entry()` / `OptionsTradeService.run_entry()`.
