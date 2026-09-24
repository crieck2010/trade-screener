# trade-screener

Multi-symbol equity screener for the [trade-suite](https://github.com/crieck2010/trade-suite) — pure-Python, stdlib-only, no NumPy, no pandas.

What it does:

- **Technical / liquidity / fundamental filters** — AND-combined `Criterion` predicates (`pe <= 20`, `rsi_14 in [30, 70]`, `dollar_vol_21 >= 1e6`, ...) with per-criterion pass/fail detail for every symbol
- **Composite z-score ranking** — weighted cross-sectional scores (`score = Σ w·m·z(m)`) so "high momentum, low vol" is one number
- **6 filter presets + 3 score presets** — momentum, value, quality, low-vol, breakout, oversold-bounce
- **Seeded demo universe** — 5 regime archetypes (uptrend / downtrend / mean-revert / high-vol / flat) so every example and test is reproducible offline
- **Suite adapters (all lazy)** — bars from trade-data-equities / trade-suite, universes from CSV, screen output shaped for trade-backtest, trade-agents, and trade-optimize

Research/backtesting/paper-trading only — never live trading, never personalized investment advice.

## Install

```bash
pip install git+https://github.com/crieck2010/trade-screener.git
```

Requires Python 3.10+. No third-party dependencies.

## Quick start

```bash
# screen the seeded demo universe with the momentum preset
trade-screener scan --demo --preset momentum

# rank it instead of filtering
trade-screener score --demo --score-preset momentum-score --top 5

# your own filters: metric:op:value (repeatable)
trade-screener scan --demo --criterion rsi_14:between:30,70 --criterion vol_63:lte:0.35

# your own tickers via the data adapters (needs trade-data-equities or trade-suite)
trade-screener scan --tickers AAPL,MSFT,NVDA --source demo --preset quality

# inspect every metric for one symbol
trade-screener metrics --demo DEMO01
```

```python
from trade_screener import demo_universe, demo_fundamentals, screen, preset_criteria, score, preset_score_spec

data = demo_universe(n=50, seed=7)
fund = demo_fundamentals(list(data), seed=7)

report = screen(data, preset_criteria("value"), fund, universe="demo-50")
print(report.passed_tickers)

ranked = score(data, preset_score_spec("quality-score"), fund)
print([(r.ticker, round(r.score, 2)) for r in ranked[:5]])
```

## CLI

```
trade-screener scan    --demo | --tickers A,B | --universe FILE [--preset NAME] [--criterion m:op:v]...
trade-screener score   --demo | --tickers A,B | --universe FILE (--score-preset NAME | --weight m=w ...)
trade-screener metrics --demo DEMO01
trade-screener presets
trade-screener license | trade-screener update-check
```

Common options: `--source demo`, `--days 300`, `--seed 7`, `--fundamentals fund.csv`, `--format table|json|csv`, `--top N`.

Criterion ops: `gte lte gt lt eq between outside`, e.g. `pe:between:0,20`, `rsi_14:outside:20,80`.

## The maths

**What you learn.** A screener answers two questions: *which symbols survive a set of rules?* (filtering) and *in what order should I look at them?* (ranking). The engine computes one metric panel per symbol — trend (SMA/EMA, price vs. moving average), momentum (21/63/126/252-day total returns), mean-reversion pressure (Wilder RSI-14), risk (annualized realized vol, Wilder ATR-14, 252-day max drawdown), liquidity (21-day mean dollar volume), and position-in-range (distance to 52-week high/low) — then applies your predicates or scores.

**Why it matters.** Every downstream quant step — backtesting, portfolio optimization, the agentic research desk — starts with a universe. A disciplined, reproducible screen is what separates "I tested my strategy on the stocks I happened to remember" from an honest result. The composite score turns vague style tilts ("quality momentum") into one auditable number per symbol.

**The maths.**

- *Momentum*: `mom_n = P_t / P_{t-n} − 1`, the n-day total simple return.
- *Wilder RSI(14)*: `100 − 100 / (1 + RS)` where `RS = avg gain / avg loss`, with both averages seeded over the first 14 bars then smoothed as `avg ← (avg·13 + today) / 14`. Pure gains → 100, pure losses → 0, flat → 50.
- *Realized volatility*: `σ_ann = stdev(log returns, n) · √252`.
- *Wilder ATR(14)*: smoothed mean of true ranges `max(H−L, |H−C_prev|, |L−C_prev|)`.
- *Max drawdown*: `min_t (P_t / max_{s≤t} P_s − 1)` — the worst peak-to-trough loss, always ≤ 0.
- *Composite score*: for each metric `m`, the cross-sectional z-score `z_i = (x_i − μ) / σ` over the scanned set (population σ; zero-variance columns score 0), then `score_i = Σ_m w_m · z_i(m)`. Positive weights reward high values; negative weights reward low ones. **Scores are relative to the scanned set, not absolute** — adding or removing symbols changes every score.
- *Filtering* is a conjunction: a symbol passes iff every criterion passes; missing data never passes.

**Honest limitations.** Z-scores are cross-sectional, so ranks are only meaningful *within* the screened set. Preset thresholds (e.g. `dollar_vol_21 ≥ $1M`) assume US large/mid-cap daily bars — recalibrate for other markets. The demo universe is synthetic and deliberately well-behaved; real data is messier. Screening many criterion combinations on the same history is data snooping — a filter that "worked" in-sample is a hypothesis, not a result, until it survives a walk-forward test in trade-backtest. Fundamentals arrive via CSV/adapter; the engine does no point-in-time alignment for you.

## Interop

| Sibling | Adapter |
|---|---|
| trade-data-equities | `bars_from_trade_data`, `tickers_from_universe` (Universe CSV or plain ticker list) |
| trade-suite | `bars_from_trade_data` fallback via the suite data service |
| trade-backtest | `to_backtest_universe` — passed tickers + criteria as a backtest universe payload |
| trade-agents | `to_agent_ideas` — each passing symbol as a research idea with a thesis string |
| trade-optimize | `metrics_for_optimize` — per-ticker `{vol_63, mom_126, ...}` panels |

All sibling imports are lazy — trade-screener imports and tests clean with nothing else installed.

## Docs

- `docs/ARCHITECTURE.md` — module map and design decisions
- `docs/METHODOLOGY.md` — metric definitions, formulas, and honest limitations
- `examples/screener_example.py` — end-to-end walkthrough

## License

MIT. See `LICENSE`.
