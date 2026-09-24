"""Tests for screening: metrics, criteria, screen, score, presets."""

import pytest

from trade_screener import (
    Criterion,
    ScoreSpec,
    apply_criteria,
    compute_metrics,
    demo_fundamentals,
    demo_universe,
    preset_criteria,
    preset_score_spec,
    score,
    screen,
    zscores,
)
from trade_screener.screen import PRESETS, SCORE_PRESETS


@pytest.fixture(scope="module")
def universe():
    return demo_universe(n=10, days=300, seed=11)


@pytest.fixture(scope="module")
def fundamentals(universe):
    return demo_fundamentals(list(universe), seed=11)


def test_compute_metrics_keys(universe):
    bars = universe["DEMO01"]
    m = compute_metrics(bars, {"pe": 15.0, "unknown_field": 99.0})
    for key in ("price", "sma_20", "sma_50", "sma_200", "mom_21", "mom_252",
                "rsi_14", "vol_21", "vol_63", "atr_14", "dollar_vol_21",
                "dist_52w_high", "dist_52w_low", "max_drawdown_252", "bars"):
        assert key in m, key
    assert m["pe"] == 15.0
    assert "unknown_field" not in m  # unrecognized fundamentals dropped
    assert m["bars"] == 300


def test_compute_metrics_short_history():
    bars = [{"close": 100.0 + i, "high": 101.0 + i, "low": 99.0 + i, "volume": 1000}
            for i in range(30)]
    m = compute_metrics(bars)
    assert m["sma_200"] is None
    assert m["sma_20"] is not None
    assert m["mom_252"] is None


def test_compute_metrics_empty():
    assert compute_metrics([]) == {"bars": 0}


def test_criterion_validation():
    with pytest.raises(ValueError):
        Criterion(metric="pe", op="approx", value=10)
    with pytest.raises(ValueError):
        Criterion(metric="pe", op="between", value=(20, 10))
    c = Criterion(metric="pe", op="between", value=(10, 20))
    assert "in [10, 20]" in c.describe()
    assert ">=" in Criterion(metric="pe", op="gte", value=10).describe()


def test_apply_criteria_and_semantics():
    metrics = {"pe": 12.0, "rsi_14": 55.0}
    crits = [Criterion("pe", "lte", 20), Criterion("rsi_14", "between", (30, 70))]
    ok, checks = apply_criteria(metrics, crits)
    assert ok and all(c["passed"] for c in checks)
    crits = [Criterion("pe", "lte", 10), Criterion("rsi_14", "between", (30, 70))]
    ok, _ = apply_criteria(metrics, crits)
    assert not ok


def test_missing_metric_never_passes():
    ok, checks = apply_criteria({}, [Criterion("pe", "lte", 20)])
    assert not ok
    assert checks[0]["observed"] is None


def test_outside_op():
    metrics = {"rsi_14": 85.0}
    ok, _ = apply_criteria(metrics, [Criterion("rsi_14", "outside", (30, 70))])
    assert ok
    ok, _ = apply_criteria({"rsi_14": 50.0}, [Criterion("rsi_14", "outside", (30, 70))])
    assert not ok


def test_screen_report_shape(universe, fundamentals):
    report = screen(universe, preset_criteria("momentum"), fundamentals, universe="demo")
    d = report.to_dict()
    assert d["universe"] == "demo"
    assert d["n_scanned"] == 10
    assert d["n_passed"] == len(d["passed_tickers"])
    assert len(d["rows"]) == 10
    row = d["rows"][0]
    assert set(row) == {"ticker", "passed", "metrics", "checks"}
    # every row records one check per criterion
    assert len(row["checks"]) == len(preset_criteria("momentum"))
    # report is JSON-serializable
    import json
    json.dumps(d)


def test_screen_unknown_preset():
    with pytest.raises(ValueError):
        preset_criteria("nope")


def test_zscores_basic():
    zs = zscores({"a": 1.0, "b": 2.0, "c": 3.0})
    assert zs["a"] == pytest.approx(-1.224744871391589)
    assert zs["b"] == pytest.approx(0.0)
    assert zs["c"] == pytest.approx(1.224744871391589)


def test_zscores_zero_variance_and_missing():
    zs = zscores({"a": 5.0, "b": 5.0, "c": None})
    assert zs == {"a": 0.0, "b": 0.0}
    assert zscores({"a": 1.0}) == {"a": 0.0}


def test_score_orders_by_composite(universe, fundamentals):
    spec = ScoreSpec({"mom_126": 1.0, "vol_63": -0.5})
    ranked = score(universe, spec, fundamentals)
    assert len(ranked) == 10
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)
    # spot-check composite math on the top row
    top = ranked[0]
    expect = sum(spec.weights[m] * top.zscores[m] for m in spec.weights)
    assert top.score == pytest.approx(expect)


def test_score_negative_weight_rewards_low_values():
    uni = {
        "LOW": [{"close": 100 * (1 + 0.0001 * i), "high": 101, "low": 99, "volume": 1_000_000}
                for i in range(300)],
        "HIGH": [{"close": 100 * (1 + 0.001 * i), "high": 101, "low": 99, "volume": 1_000_000}
                 for i in range(300)],
    }
    ranked = score(uni, ScoreSpec({"mom_126": -1.0}))
    assert ranked[0].ticker == "LOW"  # negative weight -> lower momentum wins


def test_score_deterministic(universe, fundamentals):
    spec = preset_score_spec("momentum-score")
    first = [r.ticker for r in score(universe, spec, fundamentals)]
    second = [r.ticker for r in score(universe, spec, fundamentals)]
    assert first == second


def test_score_spec_validation():
    with pytest.raises(ValueError):
        ScoreSpec({})
    with pytest.raises(ValueError):
        ScoreSpec({"mom_126": "high"})


def test_presets_all_build():
    for name in PRESETS:
        crits = preset_criteria(name)
        assert len(crits) >= 3
        for c in crits:
            assert isinstance(c, Criterion)
    for name in SCORE_PRESETS:
        spec = preset_score_spec(name)
        assert isinstance(spec, ScoreSpec)
    with pytest.raises(ValueError):
        preset_score_spec("nope")


def test_screen_value_preset_uses_fundamentals(universe, fundamentals):
    report = screen(universe, preset_criteria("value"), fundamentals)
    # every passing row must satisfy pe in [0, 20]
    for row in report.rows:
        if row.passed:
            pe = row.metrics.get("pe")
            assert pe is not None and 0.0 <= pe <= 20.0
