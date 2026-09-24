# METHODOLOGY — trade-screener

## Metric definitions

All metrics are computed by `compute_metrics(bars, fundamentals)` over daily
bars. `None` means "not enough data" (e.g. `sma_200` with 100 bars).

### Trend

| metric | definition |
|---|---|
| `sma_20/50/200` | simple mean of last n closes |
| `ema_20` | exponential MA, `k = 2/(20+1)`, seeded with SMA of first 20 |
| `price_vs_sma_50/200` | `price / sma − 1` |

### Momentum

`mom_21/63/126/252 = P_t / P_{t−n} − 1` — total simple return over ~1/3/6/12
months. Simple (not log) returns so the numbers read as percentages.

### Mean-reversion pressure

`rsi_14`: Wilder's RSI. Seed with mean gain/loss over the first 14
one-bar changes, then `avg ← (avg·13 + today)/14`. Pure gains → 100, pure
losses → 0, flat → 50. Tested against a published hand-worked example
(≈57.9).

### Risk

| metric | definition |
|---|---|
| `vol_21/63` | `stdev(log returns, n) · √252`, annualized |
| `atr_14` | Wilder-smoothed mean true range; `atr_pct = atr_14 / price` |
| `max_drawdown_252` | `min_t (P_t / max_{s≤t} P_s − 1)` ≤ 0 |
| `beta` | (fundamental) OLS slope vs. benchmark — supplied, not computed |

### Liquidity / range

| metric | definition |
|---|---|
| `dollar_vol_21` | mean(`close × volume`, 21) — the liquidity gate |
| `dist_52w_high` | `close / max(high, 252) − 1` ≤ 0 |
| `dist_52w_low` | `close / min(low, 252) − 1` ≥ 0 |

### Fundamentals (from CSV/adapter)

`pe pb ps market_cap dividend_yield beta eps_growth roe` — decimals where
applicable (`dividend_yield` 0.02 = 2%). Unrecognized fields are ignored;
unparseable values are skipped, never coerced.

## Filtering

`apply_criteria` is a conjunction: pass iff *every* criterion passes. Ops:
`gte lte gt lt eq between outside`. A `None` observed value fails the check —
filters are conservative about missing data, and the per-symbol `checks`
list shows exactly which criterion failed and what was observed.

## Composite scoring

For each weighted metric `m`, cross-sectional z-score over the scanned set:

```
z_i = (x_i − μ) / σ        (population σ; σ = 0 → z = 0; missing → omitted)
score_i = Σ_m w_m · z_i(m)
```

Rows sort by descending score, ties by ticker (deterministic). Weights are
used as given — keep magnitudes comparable. Negative weights reward low
values (e.g. `"pe": -1.0` favors cheap stocks).

## Presets

Thresholds assume daily bars and US large/mid-cap magnitudes. They are
starting points, not recommendations:

- **momentum**: 6m return ≥ 10%, above SMA-50, RSI 30–80, $1M+ dollar volume
- **value**: 0 ≤ P/E ≤ 20, P/B ≤ 3, yield ≥ 1.5%, within 20% of SMA-200
- **quality**: ROE ≥ 15%, EPS growth ≥ 5%, drawdown ≥ −30%, vol ≤ 40%
- **low-vol**: 63d vol ≤ 20%, beta ≤ 1, drawdown ≥ −25%, $1M+ dollar volume
- **breakout**: within 3% of 52w high, 2%+ above SMA-50, RSI 50–85, $2M+ volume
- **oversold-bounce**: RSI ≤ 30, within 15% of 52w low, within 35% of SMA-200

## Honest limitations

1. Scores are relative to the scanned set — not comparable across universes.
2. Preset thresholds are market-specific; recalibrate outside US equities.
3. Fundamentals are as-of-today unless you lag them (no PIT alignment).
4. Repeatedly tuning criteria on the same history is data snooping; validate
   walk-forward in trade-backtest.
5. The demo universe is synthetic and regime-clean; it exists for
   reproducibility, not realism.
