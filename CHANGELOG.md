# Changelog — trade-screener

## v0.1.0 — 2026-09-24

Initial release.

- Technical / liquidity / fundamental screening engine (stdlib-only, Python 3.10+)
- `Criterion` filters with `gte/lte/gt/lt/eq/between/outside` ops, AND semantics, per-criterion evidence per symbol
- Metric panel: SMA/EMA, price-vs-MA, 21/63/126/252-day momentum, Wilder RSI-14, annualized realized vol, Wilder ATR-14, max drawdown, 21-day dollar volume, 52-week high/low distance
- Composite z-score ranking (`ScoreSpec` weights; set-relative, deterministic)
- 6 filter presets (momentum, value, quality, low-vol, breakout, oversold-bounce) + 3 score presets
- Seeded demo universe (5 regime archetypes) + demo fundamentals for offline work
- Fundamentals CSV loader
- Lazy adapters: bars/universes from trade-data-equities or trade-suite; outputs shaped for trade-backtest, trade-agents, trade-optimize
- CLI: `scan`, `score`, `metrics`, `presets`, `license`, `update-check` (table/json/csv)
- Suite license-key / update-check hooks (stubbed, community tier)
- 57 tests; docs: README ("the maths"), ARCHITECTURE, METHODOLOGY
