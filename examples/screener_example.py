"""End-to-end trade-screener walkthrough (runs offline on demo data)."""

from trade_screener import (
    demo_fundamentals,
    demo_universe,
    preset_criteria,
    preset_score_spec,
    score,
    screen,
)
from trade_screener.adapters import to_agent_ideas, to_backtest_universe

data = demo_universe(n=20, days=300, seed=7)
fund = demo_fundamentals(list(data), seed=7)

print("=== 1. Filter: momentum preset ===")
report = screen(data, preset_criteria("momentum"), fund, universe="demo-20")
print(f"scanned {len(report.rows)}, passed {len(report.passed_tickers)}: {list(report.passed_tickers)}")
for row in report.rows:
    if row.passed:
        failed = [c["criterion"] for c in row.checks if not c["passed"]]
        assert not failed
print("every passing row satisfied every criterion")

print("\n=== 2. Rank: momentum-score composite ===")
ranked = score(data, preset_score_spec("momentum-score"), fund)
for r in ranked[:5]:
    print(f"  {r.ticker}: score {r.score:+.2f}  mom_126 {r.metrics['mom_126']:+.1%}  vol_63 {r.metrics['vol_63']:.1%}")

print("\n=== 3. Hand-off payloads ===")
print("backtest universe:", to_backtest_universe(report)["tickers"])
ideas = to_agent_ideas(report, ranked)
print(f"agent ideas: {len(ideas)}")
for idea in ideas[:3]:
    print(f"  [{idea['ticker']}] {idea['thesis']}")

print("\n=== 4. Custom screen: cheap + calm ===")
custom = screen(data, preset_criteria("value"), fund)
calm = [r.ticker for r in custom.rows
        if r.passed and (r.metrics.get("vol_63") or 9) < 0.30]
print("value names with 63d vol < 30%:", calm)
