# Atlas — Configurability Roadmap

Goal: minimum human discretion in taking trades, maximum flexibility in configuring the rules that govern them. Every item below exists because some trading-relevant parameter currently requires a code change + redeploy to touch. Ordered by priority/impact — Tier 1 unlocks the rest.

Created 2026-08-15, from a full-codebase configurability audit (not iron-condor-specific).

---

## Tier 1 — Foundational

- [x] **#22 — Strategy config editor + versioning UI** — done 2026-08-15
  `StrategyVersion.config` (JSON: `capital_pct`, `max_lots`, `strike_step`, `short_otm_pct`, `hold_days`, `atr_multiple`, etc.) is only ever set via Alembic migration (see `backend/alembic/versions/f7a3c1e9b4d2_add_account_capital_pct_to_iron_condor.py`). Changing any strategy parameter today = writing a migration. `StrategyVersion.version`/`is_active` already support versioning — no UI exists on top of it.
  Build: a page to view/edit config as a typed form (reuse the `parameter_fields` dynamic-form pattern already in `frontend/app/jobs/page.tsx`), writing a new `StrategyVersion` row rather than mutating in place (free audit trail + rollback).
  Shipped: `/strategies` page, `GET/POST /api/v1/strategies/...`, typed form for `nifty_iron_condor` (raw-JSON fallback for strategies without a registered schema), create-draft → activate flow with atomic row-locked activation. **Not yet applied to the live production DB** — the `created_at` migration needs an explicit go-ahead to run against the real Postgres (schema writes to live infra are outside auto-mode's authority). Still doesn't affect what's actually scheduled — that's TODO #23.

- [x] **#23 — DB-driven schedule + enable/disable, replacing commented-out code** — done 2026-08-15
  `backend/app/core/celery_schedule.py` is a hardcoded Python dict. The momentum screener is "disabled" by literally commenting out 3 schedule entries with a note to uncomment to resume. `Strategy.is_active`/`StrategyVersion.is_active` exist and are never read for this. Pausing/resuming or retiming a strategy = edit source + redeploy.
  Build: DB-backed schedule (Celery supports a database scheduler) with an on/off toggle and time editor in the UI.
  Shipped: `schedule_entries` table + `/schedule` page, wired to the already-installed-but-unused `celery-redbeat` (edits take effect within one beat tick, no restart — proven live against a real running local beat process during verification). Also closed the loop with #22: `iron_condor_entry`/`iron_condor_exit`/`trade_entry`/`trade_exit`/`strategy_execution` now take `strategy_id` and resolve the *active* version at run time, so activating a version in the Strategies page now actually changes what runs. All 17 existing schedule entries migrated, including the 3 commented-out momentum_screener ones (now real `enabled=False` rows). Found in passing: `momentum_screener`'s `strategies`/`strategy_versions` rows were never seeded via any migration (hand-inserted at some point) — worth a follow-up migration someday, not blocking. Live cutover (migration + `atlas-beat` restart with `-S redbeat.RedBeatScheduler`) pending your go-ahead, same as #22's DB migration.

- [x] **#24 — Global kill switch** — done 2026-08-15
  No single control halts all live order placement. Only lever today: stop the Celery beat container or comment out schedule + redeploy.
  Build: an emergency-stop flag checked at the top of every entry/exit job, independent of individual strategy configs, toggleable from the UI.
  Shipped: a persistent pill in the header (every page, one click) toggling a `kill_switch` singleton row. Scoped to **new entries only** (`iron_condor_entry`/`trade_entry`) per a deliberate call — exits, trailing stops, and gap-down emergency handling in `position_sync` keep running unaffected, so pausing never abandons risk already on the books. Pausing requires a reason (audit trail + Discord alert); resuming is one click. Fixed a real bug found during implementation: `TopNav` was rendered outside `QueryProvider` in the root layout, so any header component using React Query would have crashed the build — widened the provider's scope rather than giving the new control its own isolated query client.

## Tier 2 — Risk & capital control

- [x] **#25 — Central risk/capital dashboard** — done 2026-08-15
  `account_capital_pct` exists per-strategy (`backend/app/services/portfolio.py:38`, `get_isolated_account_size`) but there's no view showing how capital is currently split across active strategies, and nothing prevents two strategies both claiming 100% (already found once — `get_position_size` wasn't respecting it until fixed this week).
  Build: a screen showing total allocation across strategies, flags overallocation, lets you rebalance without touching JSON directly.
  Shipped: a "Capital Allocation" card on the existing `/portfolio` page — account size from the daily snapshot (deliberately not a live Kite call, which would launch a headless browser per page view), per-strategy allocated vs. deployed capital (deployed summed across every version of a strategy, not just the active one, since open positions don't move when a newer version is activated), and an unmissable red banner when combined allocation exceeds 100%. `#22`'s config editor already covers "rebalance without touching JSON" — this item was purely the missing aggregate view.

- [x] **#26 — Configurable circuit breakers (drawdown halt)** — done 2026-08-15
  Only automatic risk control was a 5% drawdown *alert* (`backend/app/services/trade.py:631`, `_check_portfolio_drawdown`, hardcoded threshold, Discord-only, equity-trades-only — doesn't stop anything and can't see the options book). Scoped to drawdown-halt only for this pass; consecutive-loss pause and gap-check-before-entry are separate future breaker types on the same table.
  Shipped: a `circuit_breakers` table (`type`/`enabled`/`params` JSON/`last_triggered_at`/`last_reason` — extensible to future rule types without a schema change), a new `PortfolioService.check_drawdown_circuit_breaker()` that walks combined realized P&L across both equity `Trade`s and options `OptionsPosition`s (new `OptionsTradeService.get_unrealized_pnl()`/`get_closed_positions_pnl()`) and — on breach — activates the #24 kill switch instead of only alerting (reuses its existing Discord notification, never auto-clears). Old equity-only drawdown methods deleted from `TradeService`; the check now runs from `position_sync.py` after every sync. `GET/PATCH /api/v1/circuit-breakers` + a "Circuit Breakers" card on `/portfolio` (toggle + editable threshold + last-triggered banner). Verified the options-only trigger path explicitly — a drawdown breaker that can't see the live iron condor was the actual gap being fixed.

- [ ] **#27 — Pluggable position-sizing models**
  Sizing is one hardcoded formula per strategy (`capital / max_positions`, or `capital * capital_pct // margin_per_lot`). No config toggle for e.g. volatility-scaled or Kelly-fraction sizing.
  Build: sizing-model registry selectable per strategy via config, mirroring the existing exit-evaluator registry pattern (`backend/app/exit_evaluators/registry.py`).

## Tier 3 — Execution & operational tuning

- [ ] **#28 — Execution parameters as config, not hardcoded constants**
  Order buffers (`ORDER_BUFFERS = {"BUY": 1.02, "SELL": 0.98}` in `options_trade.py`), poll attempts/delay (6× 5s), GTT limit buffer — all module constants in `backend/app/services/options_trade.py` and `backend/app/services/trade.py`. If option spreads widen and buffers stop filling reliably, that's a code change.
  Build: move into strategy config (low effort, meaningful flexibility gain).

- [ ] **#29 — Notification/alerting policy config**
  Discord policies (what fires vs. is suppressed, drawdown alert %, breakeven alert) are Python `if` branches in `backend/app/celery/tasks.py`.
  Build: a settings page to tune thresholds and toggle per-event notifications.

- [ ] **#30 — NSE holiday calendar, auto-sourced or DB-editable**
  `backend/app/utils/trading_calendar.py` hardcodes `NSE_HOLIDAYS` and self-alerts when coverage runs low (good stopgap) — but the fix is still "edit a Python set and redeploy" once a year.
  Build: scrape NSE's published calendar automatically, or move to a DB table editable from the UI.

## Tier 4 — Coverage & extensibility

- [ ] **#31 — Universe/watchlist configuration UI**
  Instrument scope = automatic NIFTY 500 import + one hardcoded env var (`HOLDINGS_EXCLUDE`). No UI for exclude-lists, sector filters, or per-strategy universes (e.g. restricting the iron condor to NIFTY-only vs. adding BANKNIFTY later).

- [ ] **#32 — Strategy "template" system**
  Adding any new strategy variant today = new `Strategy` subclass + possibly new exit evaluator + new Celery task class + new job file + new migration + new hardcoded schedule entry + hardcoded `strategy_version_id` module constant elsewhere (see `IRON_CONDOR_STRATEGY_VERSION_ID = 3` in `celery_schedule.py`, with a comment explaining the manual DB lookup needed to set it).
  Build: a generic templated strategy (e.g. "credit spread" with configurable legs/strikes/expiry-selection/exit-rule composition) so new variants can be spun up via config alone. Bigger architectural lift — a direction, not a quick win.

- [ ] **#33 — Paper-trading / simulation mode**
  Previously decided "won't do" (see memory). Worth revisiting once config becomes editable (Tier 1) — you'll want to test a changed `short_otm_pct` or a new circuit-breaker rule without it touching real capital immediately.

## Tier 5 — Observability & governance

- [ ] **#34 — Config change audit trail / diff view**
  Once strategy config is versioned (Tier 1), add a simple "what changed between v3 and v4" view.

- [ ] **#35 — Ops/settings page**
  Discord webhook enable + test-send button, Kite token status/expiry + manual refresh trigger, environment health at a glance. Quality-of-life, not trading-critical — hence last.

---

*Recommended starting point: #22 and #23 — almost everything else on this list becomes easier once config is a first-class, editable thing instead of buried in migrations and hardcoded Python.*
