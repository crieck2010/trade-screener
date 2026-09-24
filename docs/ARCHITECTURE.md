# ARCHITECTURE — trade-screener

## Module map

```
src/trade_screener/
    __init__.py      public surface (functions, presets, model types)
    __main__.py      python -m trade_screener
    models.py        Criterion / ScreenRow / ScreenReport / ScoredRow / ScoreSpec (frozen dataclasses)
    indicators.py    sma, ema, momentum, realized_vol, rsi_wilder, atr_wilder,
                     mean_dollar_volume, distance_to_high/low, max_drawdown, beta_vs
    screen.py        compute_metrics, apply_criteria, screen, zscores, score,
                     PRESETS, SCORE_PRESETS, preset_criteria, preset_score_spec
    fundamentals.py  load_fundamentals_csv, fundamentals_from_rows
    demo.py          demo_universe, demo_fundamentals (seeded regime archetypes)
    adapters.py      lazy sibling bridges (data in, backtest/agents/optimize out)
    cli.py           trade-screener scan|score|metrics|presets|license|update-check
    licensing.py     suite-wide license-key / update-check hooks (stubbed)
```

## Design decisions

**Plain-data contracts.** Bars are `dict`s (`date/open/high/low/close/volume`);
fundamentals are `{TICKER: {field: value}}`; reports expose `.to_dict()` and
are JSON-serializable. No DataFrames, no custom containers crossing module
boundaries — anything in the suite can consume a screen result without
importing trade-screener's internals.

**Two verbs, not one.** `screen` *filters* (boolean AND over criteria, with
per-criterion evidence per symbol); `score` *ranks* (composite z-score).
Keeping them separate means a caller can filter-then-rank, rank-only, or
filter-only without paying for the other.

**Missing data never passes.** A criterion on a metric the symbol lacks
(short history, no fundamentals row) fails that check rather than raising
or — worse — silently passing. This is the conservative default for a
research tool: you notice the gap in the `checks` detail instead of trading
on it.

**Cross-sectional scoring is set-relative.** Z-scores are computed over the
scanned set only. This is deliberate (it's what "rank this watchlist" means)
and documented as a limitation: scores are not comparable across runs with
different universes.

**Lazy adapters.** `adapters.py` imports siblings inside function bodies.
`trade_screener` imports and fully tests with zero suite packages installed;
a missing sibling raises a `RuntimeError` naming the pip URL.

**Deterministic demo.** `demo_universe`/`demo_fundamentals` take a `seed` and
produce identical output every run, so docs, examples, and tests never depend
on network or wall-clock time. The CLI defaults (`--demo`, seed 7) make the
first run work offline.

**Scaling notes.** Everything is per-symbol pure functions over lists, so a
universe of N symbols is O(N · bars) time and O(bars) peak memory per symbol
if streamed; the current `screen`/`score` materialize the full dict, which is
fine into the tens of thousands of symbols on a laptop. No parallelism yet —
the per-symbol work is the obvious place to add a process pool later without
changing any public signature.

## What v0.1.0 does NOT do

- No live data fetching (bars come from adapters/CSV/demo; free delayed data
  enters through trade-data-equities or the trade-suite data service).
- No point-in-time fundamentals alignment — treat CSV fundamentals as
  as-of-today unless you lag them yourself.
- No persistent watchlists or scheduled scans (that's a dashboard/suite job).
