"""Indicator unit tests against hand-computed values."""

import math

import pytest

from trade_screener import indicators as ind


def bars_from_closes(closes, volume=1000):
    bars = []
    for i, c in enumerate(closes):
        bars.append({
            "date": f"2025-01-{i + 1:02d}",
            "open": c, "high": c * 1.01, "low": c * 0.99,
            "close": c, "volume": volume,
        })
    return bars


def test_sma():
    assert ind.sma([1, 2, 3, 4, 5], 3) == pytest.approx(4.0)
    assert ind.sma([1, 2], 3) is None
    assert ind.sma([1, 2, 3], 0) is None


def test_ema_seed_and_update():
    # seed = SMA of first n, then one update step
    vals = [10.0, 11.0, 12.0, 13.0]
    seed = sum(vals[:3]) / 3
    k = 2 / 4
    expected = 13.0 * k + seed * (1 - k)
    assert ind.ema(vals, 3) == pytest.approx(expected)
    assert ind.ema([1.0, 2.0], 3) is None


def test_momentum():
    closes = [100.0, 110.0, 121.0]
    assert ind.momentum(closes, 2) == pytest.approx(0.21)
    assert ind.momentum([100.0], 1) is None
    assert ind.momentum([0.0, 100.0], 1) is None


def test_realized_vol_zero_for_constant_returns():
    closes = [100 * 1.001 ** i for i in range(30)]
    assert ind.realized_vol(closes, 21) == pytest.approx(0.0, abs=1e-12)


def test_realized_vol_manual():
    closes = [100.0, 101.0, 100.0, 102.0, 101.0]
    rets = [math.log(101 / 100), math.log(100 / 101), math.log(102 / 100), math.log(101 / 102)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    assert ind.realized_vol(closes, 4) == pytest.approx(math.sqrt(var * 252))


def test_rsi_all_up_is_100():
    closes = [100 + i for i in range(20)]
    assert ind.rsi_wilder(bars_from_closes(closes), 14) == pytest.approx(100.0)


def test_rsi_all_down_is_0():
    closes = [100 - i for i in range(20)]
    assert ind.rsi_wilder(bars_from_closes(closes), 14) == pytest.approx(0.0)


def test_rsi_flat_is_50():
    closes = [100.0] * 20
    assert ind.rsi_wilder(bars_from_closes(closes), 14) == pytest.approx(50.0)


def test_rsi_accepts_raw_closes():
    closes = [100 + i for i in range(20)]
    assert ind.rsi_wilder(closes, 14) == pytest.approx(100.0)


def test_rsi_known_value():
    # Investopedia-style example: alternating gains/losses
    closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
              46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64]
    assert ind.rsi_wilder(closes, 14) == pytest.approx(57.9, abs=0.6)


def test_atr_manual():
    bars = [
        {"high": 10.0, "low": 9.0, "close": 9.5},
        {"high": 11.0, "low": 9.5, "close": 10.5},
        {"high": 10.8, "low": 9.8, "close": 10.0},
    ]
    # TR1 = max(1.5, |11-9.5|, |9.5-9.5|) = 1.5
    # TR2 = max(1.0, |10.8-10.5|, |9.8-10.5|) = 1.0
    assert ind.atr_wilder(bars, 2) == pytest.approx(1.25)
    assert ind.atr_wilder(bars, 5) is None


def test_mean_dollar_volume():
    bars = bars_from_closes([10.0, 20.0, 30.0], volume=100)
    assert ind.mean_dollar_volume(bars, 3) == pytest.approx(2000.0)
    bars[0]["volume"] = None
    assert ind.mean_dollar_volume(bars, 3) is None


def test_distance_to_high_low():
    bars = bars_from_closes([100.0, 110.0, 105.0])
    assert ind.distance_to_high(bars, 3) == pytest.approx(105 / 111.1 - 1)
    assert ind.distance_to_low(bars, 3) == pytest.approx(105 / 99.0 - 1)
    assert ind.distance_to_high(bars, 3) <= 0
    assert ind.distance_to_low(bars, 3) >= 0


def test_max_drawdown():
    assert ind.max_drawdown([100, 120, 90, 110, 80], 5) == pytest.approx(80 / 120 - 1)
    assert ind.max_drawdown([100, 110, 120], 3) == pytest.approx(0.0)
    assert ind.max_drawdown([100], 5) is None


def test_beta_vs():
    bench = [0.01, 0.02, -0.01, 0.03]
    rets = [0.02, 0.04, -0.02, 0.06]  # exactly 2x
    assert ind.beta_vs(rets, bench) == pytest.approx(2.0)
    assert ind.beta_vs([0.01], [0.01]) is None
    assert ind.beta_vs([0.01, 0.02], [0.0, 0.0]) is None
